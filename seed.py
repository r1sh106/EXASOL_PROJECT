"""Made-up shops, products, customers and orders. No real businesses or brands."""

# (shop_id, shop_name, owner_name, area, phone, opens)
SHOPS = [
    ("NWG01", "New Wave Grocers", "John Smith", "Corner of Banyan St & 3rd Cross", "+91 90000 12345", "7 AM – 10 PM"),
    ("CBP02", "Corner Basket Provisions", "Asha Menon", "Lakeview Road, near the post office", "+91 90000 54321", "8 AM – 9 PM"),
]

# (product_id, shop_id, product_name, unit, price, keywords)
PRODUCTS = [
    ("NW101", "NWG01", "Sunbake Glucose Biscuits", "250 g pack", 25, "biscuit,biscuits,sunbake"),
    ("NW102", "NWG01", "Crunchmore Cashew Cookies", "200 g pack", 40, "cookies,cashew cookies,crunchmore"),
    ("NW103", "NWG01", "Dairyfresh Toned Milk", "500 ml pouch", 28, "milk,doodh,dairyfresh"),
    ("NW104", "NWG01", "Golden Paddy Sona Masoori Rice", "5 kg bag", 410, "rice,chawal,sona masoori,golden paddy"),
    ("NW105", "NWG01", "Royal Grain Basmati Rice", "1 kg", 150, "basmati,royal grain"),
    ("NW106", "NWG01", "Toor Dal", "1 kg", 160, "dal,daal,toor,tur"),
    ("NW107", "NWG01", "Moong Dal", "1 kg", 140, "moong,green gram"),
    ("NW108", "NWG01", "Onion", "1 kg", 40, "onion,onions,pyaz"),
    ("NW109", "NWG01", "Tomato", "1 kg", 30, "tomato,tomatoes,tamatar"),
    ("NW110", "NWG01", "Potato", "1 kg", 35, "potato,potatoes,aloo"),
    ("NW111", "NWG01", "Sunvita Sunflower Oil", "1 L", 155, "oil,sunflower oil,sunvita"),
    ("NW112", "NWG01", "Seabreeze Salt", "1 kg", 28, "salt,namak"),
    ("NW113", "NWG01", "Eggs", "tray of 12", 84, "egg,eggs,anda"),
    ("NW114", "NWG01", "Hearthloaf Bread", "400 g", 45, "bread"),
    ("NW115", "NWG01", "Millstone Atta", "5 kg bag", 285, "atta,wheat flour,flour"),
    ("NW116", "NWG01", "Sugar", "1 kg", 48, "sugar,cheeni"),
    ("NW117", "NWG01", "Leafy Gold Tea", "250 g", 140, "tea,chai,chai patti"),
    ("NW118", "NWG01", "Bean Bloom Coffee Powder", "200 g", 180, "coffee"),
    ("NW119", "NWG01", "Fresh Set Curd", "400 g cup", 35, "curd,dahi,yogurt"),
    ("NW120", "NWG01", "Soft Cube Paneer", "200 g", 90, "paneer"),
    ("NW121", "NWG01", "Sparkle Dishwash Bar", "1 bar", 20, "dishwash,vessel soap,bar"),
    ("NW122", "NWG01", "Cloudsoft Bath Soap", "1 bar", 38, "soap,bath soap"),
    ("NW123", "NWG01", "Turmeric Powder", "100 g", 32, "turmeric,haldi"),
    ("NW124", "NWG01", "Chilli Powder", "100 g", 40, "chilli powder,mirchi powder,red chilli"),
    ("NW125", "NWG01", "Coriander Bunch", "1 bunch", 10, "coriander,dhania,kothimbir"),

    ("CB201", "CBP02", "Morning Pail Milk", "500 ml pouch", 27, "milk,doodh"),
    ("CB202", "CBP02", "Riverbend Ponni Rice", "5 kg bag", 380, "rice,ponni"),
    ("CB203", "CBP02", "Toor Dal", "1 kg", 158, "dal,toor"),
    ("CB204", "CBP02", "Onion", "1 kg", 38, "onion,onions"),
    ("CB205", "CBP02", "Groundnut Oil", "1 L", 190, "oil,groundnut oil"),
    ("CB206", "CBP02", "Sugar", "1 kg", 47, "sugar"),
    ("CB207", "CBP02", "Leafy Gold Tea", "250 g", 140, "tea,chai"),
    ("CB208", "CBP02", "Sunbake Glucose Biscuits", "250 g pack", 25, "biscuit,biscuits"),
    ("CB209", "CBP02", "Eggs", "tray of 12", 82, "egg,eggs"),
    ("CB210", "CBP02", "Milk Bread", "400 g", 40, "bread"),
]
OUT_OF_STOCK = {"NW118"}

# (customer_id, name, phone, address)
CUSTOMERS = [
    (1, "Meena Iyer", "9876500001", "Flat 204, ABC Apartments"),
    (2, "Ravi Kumar", "9876500002", "12, 3rd Cross, Banyan Street"),
    (3, "Farah Khan", "9876500003", "Flat 7B, Lakeview Residency"),
    (4, "Suresh Patil", "9876500004", "House 41, Temple Road"),
]

# (shop, customer, state, channel, minutes ago, transcript, [(product, qty, as written)])
ORDERS = [
    ("NWG01", 2, "completed", "voice", 300, "Send 2 milk, one bread and 6 eggs.", [("NW103", 2, "2 milk"), ("NW114", 1, "one bread"), ("NW113", 1, "6 eggs")]),
    ("NWG01", 4, "completed", "photo", 250, "Atta 5kg\nSugar 1kg\nTea\nTurmeric", [("NW115", 1, "Atta 5kg"), ("NW116", 1, "Sugar 1kg"), ("NW117", 1, "Tea"), ("NW123", 1, "Turmeric")]),
    ("NWG01", 3, "completed", "text", 190, "rice 1 bag, toor dal 2, oil", [("NW104", 1, "rice 1 bag"), ("NW106", 2, "toor dal 2"), ("NW111", 1, "oil")]),
    ("NWG01", 1, "completed", "voice", 140, "Two biscuits, milk two packets and curd.", [("NW101", 2, "two biscuits"), ("NW103", 2, "milk two packets"), ("NW119", 1, "curd")]),
    ("NWG01", 2, "ready", "photo", 45, "Onion 2kg\nTomato 1kg\nPotato 2kg\nDhania", [("NW108", 2, "Onion 2kg"), ("NW109", 1, "Tomato 1kg"), ("NW110", 2, "Potato 2kg"), ("NW125", 1, "Dhania")]),
    ("NWG01", 4, "pending", "voice", 12, "Need paneer 2, one dishwash bar and bath soap 3.", [("NW120", 2, "paneer 2"), ("NW121", 1, "one dishwash bar"), ("NW122", 3, "bath soap 3")]),
    ("CBP02", 3, "completed", "text", 200, "milk 3, bread, eggs", [("CB201", 3, "milk 3"), ("CB210", 1, "bread"), ("CB209", 1, "eggs")]),
    ("CBP02", 1, "pending", "photo", 20, "Ponni rice\nGroundnut oil 1L\nSugar", [("CB202", 1, "Ponni rice"), ("CB205", 1, "Groundnut oil 1L"), ("CB206", 1, "Sugar")]),
]
