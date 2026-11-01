"""Made-up neighbourhood data for the Knode demo. No real shops or brands."""

CUSTOMER = {"customer_id": "C1", "customer_name": "Meena", "address": "Flat 204, ABC Apartments, Banyan Street"}

# has_knode=False shops can be onboarded live in the demo
SHOPS = [
    dict(shop_id="S1", shop_name="New Wave Grocers", kind="Grocery", owner_name="John Smith", bot_phone="+91 90000 12345",
         landmark="Corner of Banyan St & 3rd Cross", distance_m=120, years_open=18, has_knode=True,
         tagline="Rice, dal, oil and daily needs"),
    dict(shop_id="S2", shop_name="Inkwell Stationers", kind="Stationery", owner_name="Priya Nair", bot_phone="+91 90000 23456",
         landmark="Opposite Little Oaks School", distance_m=250, years_open=26, has_knode=True,
         tagline="School and office supplies"),
    dict(shop_id="S3", shop_name="Sunrise Dairy Corner", kind="Dairy", owner_name="Venkat Rao", bot_phone="+91 90000 34567",
         landmark="Next to ABC Apartments gate", distance_m=80, years_open=31, has_knode=False,
         tagline="Milk, curd and paneer since sunrise"),
    dict(shop_id="S4", shop_name="Green Basket Vegetables", kind="Vegetables", owner_name="Ramu Gowda", bot_phone="+91 90000 45678",
         landmark="Banyan St footpath stall", distance_m=60, years_open=15, has_knode=False,
         tagline="Fresh vegetables every morning"),
    dict(shop_id="S5", shop_name="Golden Crust Bakery", kind="Bakery", owner_name="Fatima Sheikh", bot_phone="+91 90000 56789",
         landmark="2nd Cross, near the bus stop", distance_m=400, years_open=12, has_knode=False,
         tagline="Buns, rusks and cakes baked daily"),
    dict(shop_id="S6", shop_name="Petal & Pooja Flowers", kind="Flowers", owner_name="Lakshmi Amma", bot_phone="+91 90000 67890",
         landmark="Temple Road, by the steps", distance_m=300, years_open=40, has_knode=False,
         tagline="Garlands and loose flowers"),
    dict(shop_id="S7", shop_name="Fixit Hardware & Electricals", kind="Hardware", owner_name="Daniel Joseph", bot_phone="+91 90000 78901",
         landmark="Main Road, 4th Cross", distance_m=650, years_open=22, has_knode=False,
         tagline="Bulbs, taps, tools and fittings"),
]

# (product_id, shop_id, product_name, cat, cat_words, aliases, price, cost, stock)
# cat_words: what customers say for the category; aliases: names that pick this exact product
PRODUCTS = [
    ("P101", "S1", "Sunbake Glucose Biscuits 250g", "biscuits", "biscuits,biscuit", "sunbake", 25, 21, 40),
    ("P102", "S1", "Crunchmore Cashew Cookies 200g", "biscuits", "biscuits,biscuit", "crunchmore,cookies", 40, 33, 22),
    ("P103", "S1", "Dairyfresh Toned Milk 500ml", "milk", "milk,doodh", "dairyfresh", 28, 25, 30),
    ("P104", "S1", "Golden Paddy Sona Masoori 5kg", "rice", "rice,chawal", "golden paddy,sona masoori,sona", 410, 355, 12),
    ("P105", "S1", "Royal Grain Basmati 1kg", "rice", "rice,chawal", "royal grain,basmati", 150, 126, 8),
    ("P106", "S1", "Toor Dal 1kg", "dal", "dal,daal", "toor", 160, 138, 15),
    ("P107", "S1", "Onion 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "onions,onion", 40, 30, 25),
    ("P108", "S1", "Tomato 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "tomatoes,tomato", 30, 21, 20),
    ("P109", "S1", "Potato 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "potatoes,potato,aloo", 35, 26, 6),
    ("P110", "S1", "Sunvita Sunflower Oil 1L", "oil", "oil", "sunvita,sunflower", 155, 138, 10),
    ("P111", "S1", "Seabreeze Salt 1kg", "salt", "salt", "seabreeze", 28, 24, 30),
    ("P112", "S1", "Eggs, tray of 12", "eggs", "eggs,egg", "", 84, 72, 14),
    ("P113", "S1", "Hearthloaf Bread 400g", "bread", "bread", "hearthloaf", 45, 39, 7),
    ("P114", "S1", "Millstone Atta 5kg", "atta", "atta,flour", "millstone", 285, 252, 9),
    ("P115", "S1", "Sugar 1kg", "sugar", "sugar", "", 48, 43, 18),

    ("P201", "S2", "Brightline Notebook 200 pages", "notebook", "notebooks,notebook,books,book", "brightline", 60, 45, 80),
    ("P202", "S2", "Swiftink Blue Pen", "pen", "pens,pen", "swiftink,blue pen", 10, 7, 200),
    ("P203", "S2", "Swiftink Black Pen", "pen", "pens,pen", "black pen", 10, 7, 120),
    ("P204", "S2", "Graphix HB Pencils, pack of 10", "pencil", "pencils,pencil", "graphix", 50, 38, 40),
    ("P205", "S2", "Clearcut Eraser", "eraser", "erasers,eraser,rubber", "clearcut", 5, 3, 150),
    ("P206", "S2", "Stickwell Glue Stick", "glue", "glue", "stickwell", 25, 18, 35),
    ("P207", "S2", "Papyra A4 Paper, 500 sheets", "paper", "paper,a4", "papyra", 280, 240, 10),
    ("P208", "S2", "Compass Geometry Box", "geometry", "geometry box,geometry,compass box", "", 120, 92, 5),
    ("P209", "S2", "Rainbow Colour Pencils, 12", "colours", "colours,colors,colour pencils,crayons", "rainbow", 90, 68, 18),
    ("P210", "S2", "Brown Cover Roll", "cover", "brown cover,cover,covers", "", 30, 21, 25),

    ("P301", "S3", "Morning Pail Toned Milk 500ml", "milk", "milk,doodh", "morning pail", 27, 24, 60),
    ("P302", "S3", "Fresh Set Curd 400g", "curd", "curd,dahi,yogurt", "fresh set", 35, 28, 30),
    ("P303", "S3", "Soft Cube Paneer 200g", "paneer", "paneer", "soft cube", 90, 74, 15),
    ("P304", "S3", "Meadow Butter 100g", "butter", "butter", "meadow", 56, 48, 20),
    ("P305", "S3", "Pure Drop Ghee 500ml", "ghee", "ghee", "pure drop", 330, 290, 8),
    ("P306", "S3", "Eggs, tray of 12", "eggs", "eggs,egg", "", 84, 72, 20),

    ("P401", "S4", "Onion 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "onions,onion", 38, 28, 40),
    ("P402", "S4", "Tomato 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "tomatoes,tomato", 28, 19, 35),
    ("P403", "S4", "Potato 1kg", "veg", "vegetables,vegetable,veggies,sabzi", "potatoes,potato,aloo", 33, 24, 40),
    ("P404", "S4", "Carrot 500g", "carrot", "carrots,carrot", "", 30, 20, 20),
    ("P405", "S4", "Coriander bunch", "herbs", "coriander,dhania", "", 10, 5, 30),
    ("P406", "S4", "Green Chilli 100g", "chilli", "chillies,chilli,chili", "", 8, 4, 25),
    ("P407", "S4", "Lemon, 4 pieces", "lemon", "lemons,lemon", "", 20, 12, 30),

    ("P501", "S5", "Milk Bread 400g", "bread", "bread", "milk bread", 40, 30, 15),
    ("P502", "S5", "Sweet Bun, 4 pack", "bun", "buns,bun", "sweet bun", 35, 24, 20),
    ("P503", "S5", "Crisp Toast Rusk 300g", "rusk", "rusk,rusks,toast", "crisp toast", 60, 44, 18),
    ("P504", "S5", "Butter Cookies 250g", "cookies", "cookies,biscuits,biscuit", "butter cookies", 120, 85, 12),
    ("P505", "S5", "Plum Cake 500g", "cake", "cake,cakes", "plum", 220, 160, 6),

    ("P601", "S6", "Jasmine string, 1 metre", "flowers", "flowers,flower,jasmine,mallige", "jasmine", 40, 25, 30),
    ("P602", "S6", "Marigold garland", "garland", "garland,garlands,haar", "marigold", 60, 38, 15),
    ("P603", "S6", "Rose, loose 250g", "rose", "roses,rose", "", 80, 55, 10),
    ("P604", "S6", "Tulsi leaves bunch", "tulsi", "tulsi,basil", "", 10, 5, 25),
    ("P605", "S6", "Banana leaves, 5", "leaves", "banana leaves,leaves,leaf", "", 25, 15, 20),

    ("P701", "S7", "Brightglow LED Bulb 9W", "bulb", "bulbs,bulb,light", "brightglow", 110, 82, 30),
    ("P702", "S7", "Flexwire Extension Board", "extension", "extension board,extension,plug board", "flexwire", 450, 360, 6),
    ("P703", "S7", "Steelgrip Screwdriver Set", "screwdriver", "screwdriver,screwdrivers", "steelgrip", 220, 165, 8),
    ("P704", "S7", "Tight Seal Tape", "tape", "tape,teflon tape", "tight seal", 30, 18, 40),
    ("P705", "S7", "Powercell AA Batteries, 4", "battery", "batteries,battery,cells", "powercell", 80, 60, 25),
    ("P706", "S7", "Brass Tap Washer, 10", "washer", "washers,washer", "", 25, 14, 30),
]

# Meena's usual buys at each shop. Several rows for one category = she buys them together.
HISTORY = [
    ("C1", "S1", "biscuits", "P101", 2), ("C1", "S1", "rice", "P104", 1), ("C1", "S1", "oil", "P110", 1),
    ("C1", "S1", "milk", "P103", 2), ("C1", "S1", "dal", "P106", 1), ("C1", "S1", "atta", "P114", 1),
    ("C1", "S1", "veg", "P107", 1), ("C1", "S1", "veg", "P108", 1), ("C1", "S1", "veg", "P109", 1),
    ("C1", "S2", "notebook", "P201", 4), ("C1", "S2", "pen", "P202", 5), ("C1", "S2", "pencil", "P204", 1),
    ("C1", "S3", "milk", "P301", 2), ("C1", "S3", "curd", "P302", 1),
    ("C1", "S4", "veg", "P401", 1), ("C1", "S4", "veg", "P402", 1), ("C1", "S4", "veg", "P403", 1),
]

# (shop_id, customer_name, balance, days_open)
KHATA = [
    ("S1", "Meena", 320, 6), ("S1", "Ravi Kumar", 1240, 12), ("S1", "Lakshmi Hostel", 4850, 38), ("S1", "Arjun, Flat 12", 0, 0),
    ("S2", "Meena", 150, 9), ("S2", "Little Oaks School office", 6200, 41), ("S2", "Kiran, Flat 7", 90, 3),
    ("S3", "Meena", 410, 14), ("S3", "Ravi Kumar", 760, 20),
    ("S4", "Meena", 0, 0), ("S4", "Banyan Mess", 1800, 25),
    ("S5", "Meena", 0, 0), ("S5", "Corner Tea Stall", 950, 33),
    ("S6", "Meena", 60, 4), ("S6", "Temple office", 2400, 45),
    ("S7", "Meena", 0, 0), ("S7", "ABC Apartments Association", 3100, 52),
]

# (routine_id, shop_id, customer_name, items "product:qty,...", due_minute, schedule_label, status)
ROUTINES = [
    ("R1", "S1", "Ravi Kumar", "P103:2,P113:1", 7 * 60 + 30, "Every day, 7:30 AM", "pending"),
    ("R2", "S1", "Lakshmi Hostel", "P101:10", 11 * 60, "Every day, 11:00 AM", "pending"),
    ("R3", "S1", "Meena", "P103:2", 6 * 60 + 30, "Every day, 6:30 AM", "done"),
    ("R4", "S2", "Little Oaks School office", "P207:2", 10 * 60, "Every Monday, 10:00 AM", "pending"),
    ("R5", "S3", "Meena", "P301:2", 6 * 60, "Every day, 6:00 AM", "done"),
    ("R6", "S3", "Banyan Mess", "P302:5", 8 * 60, "Every day, 8:00 AM", "pending"),
    ("R7", "S6", "Temple office", "P602:4", 6 * 60 + 30, "Every day, 6:30 AM", "pending"),
]

# Six months of sales per shop: (sales, profit, orders, phone order %) from May to October 2026.
MONTH_LABELS = ["2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01"]
MONTHLY = {
    "S1": [(182400, 23700, 612, 18), (176900, 22100, 590, 26), (191300, 25400, 640, 34), (204800, 27900, 688, 41), (198600, 26800, 671, 47), (221500, 31200, 742, 55)],
    "S2": [(64200, 15100, 410, 12), (98800, 23400, 655, 20), (71500, 16900, 470, 28), (60300, 14200, 402, 33), (58800, 13700, 390, 38), (66900, 15800, 431, 44)],
    "S3": [(88400, 10200, 1480, 0), (86100, 9900, 1452, 0), (89900, 10400, 1501, 0), (91200, 10600, 1530, 0), (90300, 10500, 1514, 0), (93800, 10900, 1566, 0)],
    "S4": [(41200, 11800, 980, 0), (39800, 11200, 951, 0), (43600, 12500, 1022, 0), (45100, 12900, 1060, 0), (42700, 12100, 1003, 0), (47300, 13600, 1101, 0)],
    "S5": [(52400, 15900, 870, 0), (49800, 15100, 822, 0), (51200, 15500, 845, 0), (55900, 17000, 901, 0), (54100, 16400, 880, 0), (71800, 21900, 1104, 0)],
    "S6": [(28400, 10100, 640, 0), (26900, 9500, 612, 0), (30100, 10700, 668, 0), (35800, 12800, 760, 0), (39200, 14000, 812, 0), (44600, 15900, 902, 0)],
    "S7": [(73400, 17600, 220, 0), (70100, 16800, 211, 0), (68800, 16500, 207, 0), (75200, 18000, 226, 0), (72600, 17400, 219, 0), (81900, 19600, 240, 0)],
}

# Counter sales already made this morning before the demo starts: (sales, profit, orders)
TODAY_BASELINE = {"S1": (4380, 610, 14), "S2": (1240, 290, 9), "S3": (3900, 450, 41), "S4": (1650, 470, 38),
                  "S5": (2100, 640, 27), "S6": (980, 350, 19), "S7": (1450, 340, 4)}

# Sample orders the customer can send to each shop in the demo (UI content, not stored in the DB)
SAMPLES = {
    "S1": {"voice": "Hi, send rice, two packets biscuits, vegetables and one litre oil. Put it on my account.",
           "text": "milk 2, eggs, 1kg toor dal, salt", "photo": "Atta 5kg\nSugar 1 kg\nBread\nBiscuits 3"},
    "S2": {"voice": "Hello madam, my son needs notebooks, pens, one geometry box and glue for school. Add it to my account.",
           "text": "2 black pen, 1 eraser, brown cover 3", "photo": "Notebooks 6\nPencils\nColour pencils\nA4 paper 1"},
    "S3": {"voice": "Anna, send milk and curd, and 1 paneer please.", "text": "2 butter, ghee, eggs", "photo": "Milk 4\nCurd 2\nPaneer"},
    "S4": {"voice": "Send vegetables and coriander, also lemons.", "text": "carrot 2, green chilli, coriander",
           "photo": "Onion 2kg\nTomato 1kg\nCarrot\nCoriander 2"},
    "S5": {"voice": "Hi, I need bread, one plum cake and rusk. Put it on my account.", "text": "sweet bun 2, butter cookies",
           "photo": "Bread 2\nRusk\nBuns"},
    "S6": {"voice": "Amma, send jasmine 2 metres and one marigold garland for pooja.", "text": "rose, tulsi, banana leaves",
           "photo": "Garland 2\nJasmine 3 metres\nTulsi"},
    "S7": {"voice": "Hello, send two LED bulbs and one tape. Add it to my account.", "text": "batteries 2, extension board",
           "photo": "Bulb 3\nWasher\nScrewdriver set"},
}

# Share of October sales each product made, used to build the top sellers list
TOP_SHARE = [0.176, 0.098, 0.090, 0.077, 0.065]
