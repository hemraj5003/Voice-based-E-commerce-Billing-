from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")

db = client["voice_billing"]

products = db["products"]


PRODUCTS = [
    {"name":"rice","price":60,"unit":"kg","stock":100},
    {"name":"atta","price":45,"unit":"kg","stock":100},
    {"name":"dal","price":110,"unit":"kg","stock":100},
    {"name":"milk","price":25,"unit":"liter","stock":100},
    {"name":"potato","price":30,"unit":"kg","stock":100},
    {"name":"tomato","price":40,"unit":"kg","stock":100},
    {"name":"onion","price":35,"unit":"kg","stock":100},
    {"name":"banana","price":60,"unit":"dozen","stock":100},
    {"name":"apple","price":120,"unit":"kg","stock":100},
    {"name":"maggi","price":14,"unit":"packet","stock":100},
    {"name":"bread","price":40,"unit":"loaf","stock":100},
    {"name":"biscuit","price":30,"unit":"packet","stock":100},
    {"name":"tea","price":200,"unit":"250g","stock":100},
    {"name":"coffee","price":250,"unit":"200g","stock":100},
    {"name":"salt","price":25,"unit":"kg","stock":100},
    {"name":"sugar","price":45,"unit":"kg","stock":100},
    {"name":"oil","price":140,"unit":"liter","stock":100},
    {"name":"egg","price":7,"unit":"piece","stock":500}
]


def seed():

    for p in PRODUCTS:

        exists = products.find_one({"name": p["name"]})

        if not exists:

            products.insert_one(p)

            print("Inserted:", p["name"])

        else:

            print("Already exists:", p["name"])


if __name__ == "__main__":

    print("Connected to MongoDB")

    seed()

    print("Done")