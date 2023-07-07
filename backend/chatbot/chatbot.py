import os
import random
import json
import pickle
import numpy as np
import nltk
from nltk import ne_chunk, pos_tag, word_tokenize
from nltk.tree import Tree
from nltk.stem import WordNetLemmatizer
from keras.models import load_model

import sys
sys.path.append("C:/Users/pedro/Documents/Codes/Python/PAA/paa-chatbot/backend")

from database import db


lemmatizer = WordNetLemmatizer()

intents_path = os.path.join(os.path.dirname(__file__), 'intents.json')
with open(intents_path) as file:
  intents = json.load(file)

words_path = os.path.join(os.path.dirname(__file__), 'words.pkl')
with open(words_path, 'rb') as file:
  words = pickle.load(file)

classes_path = os.path.join(os.path.dirname(__file__), 'classes.pkl')
with open(classes_path, 'rb') as file:
  classes = pickle.load(file)

model_path = os.path.join(os.path.dirname(__file__), 'chatbot_model.h5')
model = load_model(model_path)

def clean_up_sentence(sentence):
  sentence_words = nltk.word_tokenize(sentence)
  sentence = [lemmatizer.lemmatize(word) for word in sentence_words]

  return sentence_words

def not_found_handle():
  return "apologies", " "

def category_not_determined():
  return "apologies"

def classify_noun(noun):  
  people = db.peoples.find_one({"name": noun})
  if people:
    return "peoples"
  
  species = db.species.find_one({"name": noun})
  if species:
    return "species"

  vehicles = db.vehicles.find_one({"name": noun})
  if vehicles:
    return "vehicles"

  planets = db.planets.find_one({"name": noun})
  if planets:
    return "planets"

  return None

def bag_of_words(sentence):
  sentence_words = clean_up_sentence(sentence)
  bag = [0] * len(words)

  for w in sentence_words:
    for i, word in enumerate(words):
      if word == w:
        bag[i] = i
  return np.array(bag)

def predict_class(sentence):
  bow = bag_of_words(sentence)
  res = model.predict(np.array([bow]))[0]

  ERROR_THRESHOLD = 0.25
  results = [[i,r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
  results.sort(key=lambda x: x[1], reverse=True)
  return_list = []

  for r in results:
    return_list.append({'intent': classes[r[0]], 'probability': str(r[1])})
  return return_list

def get_response(intents_list, intents_json, message):
  nltk_results = ne_chunk(pos_tag(word_tokenize(message)))
  noun = extract_noun(nltk_results)
  print("noun:", noun)
  print('Intents List:', intents_list)

  tag = intents_list[0]['intent']
  category = classify_noun(noun.lower())
  query = {"name": noun.lower()}

  if category:
    collection = db[category]
    query_res = collection.find_one(query)
    print("query_res", query_res)
    print("tag", tag)
    print("query_res", query_res and tag in query_res)

    if tag in query_res:
      res = query_res[tag]
    else:
      tag, res = not_found_handle()
  else:
    res = category_not_determined()

  list_of_intents = intents_json['intents']
  result = find_result(tag, res, list_of_intents, noun)

  return result

def extract_noun(nltk_results):
  noun = ''
  for nltk_result in nltk_results:
    if isinstance(nltk_result, Tree):
      name = ' '.join([nltk_result_leaf[0] for nltk_result_leaf in nltk_result.leaves()])
      noun = name
      print('Type:', nltk_result.label(), 'Name:', name)
  return noun

def find_result(tag, res, list_of_intents, character):
  for intent in list_of_intents:
    if intent['tag'] == tag:
      if isinstance(res, list):
        res = ", ".join(res)
        result = random.choice(intent['responses']['multiple'])
      else:
        result = random.choice(intent['responses']['singular'])
      result = result.replace("{name}", character)
      result = result.replace("{response}", res)
  return result

if __name__ == '__main__':
  print('GO, BOT IS RUNNING')
  counter = 0
  max_iterations = 5

  while counter < max_iterations:
    message = input('')
    ints = predict_class(message)
    print('message', message)
    print('ints', ints)
    res = get_response(ints, intents, message)
    print(res)
    counter += 1
