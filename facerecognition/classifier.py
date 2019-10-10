from sklearn.linear_model import LogisticRegression

from facerecognition.storage_factory import get_storage
import numpy as np
from threading import Thread
import logging

logging.basicConfig(level=logging.DEBUG)

models = {}


def train_async(api_key):
    thread = Thread(target=train, daemon=False, args=[api_key])
    thread.start()


def initial_train():
    api_keys = get_storage().get_api_keys()
    if not api_keys:
        return
    for api_key in api_keys:
        train(api_key)


def train(api_key):
    logging.debug('Reading training data from mongo')
    values, labels, face_names = get_storage().get_train_data(api_key)
    if len(face_names) <= 1:
        logging.warning("Not enough training data, model hasn't been created")
        return
    logging.debug('Training classifier, api key: %s' % api_key)
    model_temp = LogisticRegression(C=100000, solver='lbfgs', multi_class='multinomial')
    model_temp.fit(values, labels)
    logging.debug('Training finished, api key: %s' % api_key)
    models[api_key] = {
        "model": model_temp,
        "face_names": face_names
    }




def classify_many(embedding, api_key, box):
    if api_key not in models:
        raise RuntimeError("There is no model for api key %s." % api_key)
    model_data = models[api_key]
    predictions = model_data["model"].predict_proba([embedding])[0]
    logging.debug("predictions:")
    best_class_indices = np.argsort(-predictions)
    best_class_probability = predictions[best_class_indices[0]]
    logging.debug('Best guess: %s with probability %.5f' % (
        model_data["face_names"][best_class_indices[0]], best_class_probability))
    logging.debug('Second guess: %s with probability %.5f' % (
        model_data["face_names"][best_class_indices[1]], predictions[best_class_indices[1]]))
    return {
        "box parameters": box,
        "prediction": model_data["face_names"][best_class_indices[0]],
        "probability": best_class_probability
    }

def get_face_name(api_key):
    logging.debug('Retrieving the data from the database')
    listOfFaces = get_storage().get_all_face_name(api_key)
    if len(listOfFaces) == 0:
        logging.warning('No faces found in the database for this api-key')
    return listOfFaces


def delete_record(api_key, face_name):
    logging.debug('Looking for the record in the database and deleting it')
    get_storage().delete(api_key, face_name)
    logging.debug('Records were successfully deleted')
