from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["chatbot_saas"]

users_col = db["users"]
chat_col = db["chat_history"]
usage_col = db["usage"]