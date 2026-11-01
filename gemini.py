"""Order parsing with the Gemini API, using the official google-genai SDK."""
import os
import re
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class OrderLine(BaseModel):
    raw_text: str = Field(description="The item exactly as the customer wrote or said it, including any quantity words")
    product_id: Optional[str] = Field(description="product_id of the matching catalog item, or null if the shop does not sell it")
    item_name: str = Field(description="Clean item name in English")
    quantity: float = Field(description="How many catalog units to pack, see the rules")
    unit: Optional[str] = Field(description="The catalog unit when matched, otherwise the unit the customer used")


class ParsedOrder(BaseModel):
    transcript: str = Field(description="Everything the customer wrote or said, word for word, in the original language")
    language: str = Field(description="Language(s) the customer used, e.g. English, Hindi, Kannada, Hinglish")
    items: list[OrderLine]
    customer_note: Optional[str] = Field(description="Delivery or other instructions that are not items, or null")


CHANNELS = {
    "photo": "a photo of a handwritten shopping list",
    "voice": "a voice recording of the customer reading out their order",
    "text": "a typed message",
}

PROMPT = """You read grocery orders for a small neighbourhood shop in India. The customer sent {channel}.

Shop catalog (product_id | name | unit | price):
{catalog}

Rules:
- List every item the customer asked for, in their order. Ignore greetings and small talk.
- Match each item to the catalog by meaning, not exact spelling. Generic words ("oil", "rice", "dal", "biscuits") match the closest catalog item. Local-language names count too (aloo = potato, dhania = coriander, doodh = milk).
- If the shop does not sell an item, still list it with product_id null.
- quantity is the number of catalog units to pack. "Onion 2kg" with unit "1 kg" is 2. "Atta 5kg" with unit "5 kg bag" is 1. "6 eggs" with unit "tray of 12" is 1. Use 1 when no quantity is given. Never use 0.
- Handwriting may be messy and voice notes may mix languages. Make your best reading and keep raw_text close to what the customer wrote or said.
"""


def enabled():
    return bool(os.environ.get("GEMINI_API_KEY"))


def model_name():
    return os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def models_to_try():
    """The main model first, then fallbacks for when it is overloaded."""
    fallbacks = os.environ.get("GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.5-flash,gemini-flash-latest")
    out = [model_name()] + [m.strip() for m in fallbacks.split(",") if m.strip()]
    return list(dict.fromkeys(out))


_client = None


def client():
    global _client
    if _client is None:
        # Fail fast on a busy model so the next one can be tried, instead of long SDK retries
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(
            timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1)))
    return _client


def is_busy(err):
    """Overloaded, rate-limited or timed out: worth trying the next model."""
    s = str(err)
    return any(k in s for k in ("503", "UNAVAILABLE", "overloaded", "high demand", "429", "RESOURCE_EXHAUSTED",
                                "504", "DEADLINE_EXCEEDED", "timed out", "Timeout"))


def parse_order(catalog, channel, data=None, mime_type=None, text=None):
    """Send the upload and the shop's catalog to Gemini. Returns (ParsedOrder, model that answered)."""
    listing = "\n".join(f"{p['product_id']} | {p['product_name']} | {p['unit']} | Rs {p['price']}" for p in catalog)
    contents = []
    if data:
        contents.append(types.Part.from_bytes(data=data, mime_type=mime_type))
    if text:
        contents.append("Customer's message:\n" + text)
    contents.append(PROMPT.format(channel=CHANNELS.get(channel, CHANNELS["text"]), catalog=listing))
    config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=ParsedOrder, temperature=0.1)
    models = models_to_try()
    for n, model in enumerate(models):
        try:
            resp = client().models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            if is_busy(e) and n < len(models) - 1:
                continue
            raise
        parsed = resp.parsed if isinstance(resp.parsed, ParsedOrder) else ParsedOrder.model_validate_json(resp.text)
        return parsed, model


NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10}


def parse_typed_without_ai(catalog, text):
    """Keyword matcher used only when no Gemini key is set, so typed orders still work in a demo."""
    lines = []
    for seg in re.split(r",|\n|;|\band\b|\balso\b", text):
        s = seg.strip().lower()
        if not s:
            continue
        hit = None
        for p in catalog:
            words = [w.strip() for w in (p["keywords"] or "").split(",") if w.strip()]
            if any(re.search(r"\b" + re.escape(w) + r"\b", s) for w in words):
                hit = p
                break
        n = re.search(r"\b(\d+(?:\.\d+)?)\b(?!\s*(?:kg|g|ml|l)\b)", s) or re.search(r"\b(a|an|one|two|three|four|five|six|ten)\b", s)
        qty = float(NUMW.get(n.group(1), n.group(1))) if n else 1
        u = re.search(r"(\d+(?:\.\d+)?)\s*(kg|l)\b", s)
        if u and hit and hit["unit"].startswith("1 "):  # "onion 2kg" with unit "1 kg" = 2
            qty = float(u.group(1))
        lines.append(OrderLine(raw_text=seg.strip(), product_id=hit["product_id"] if hit else None,
                               item_name=hit["product_name"] if hit else seg.strip().capitalize(), quantity=qty or 1,
                               unit=hit["unit"] if hit else None))
    return ParsedOrder(transcript=text, language="English", items=lines, customer_note=None)
