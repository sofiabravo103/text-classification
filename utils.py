import random
from .feature_extractors.bag_of_words import BagOfWords
from .models.intention import IntentionModel
from .preprocessors.twitter_spanish import TwitterPreprocessingInSpanish


def get_api_info_from_csv(filename, csv_content_relevance=[1, 2, 3, 4]):
    """
    Get information to initialize twitter api from a csv file. The paramenter
     csv_content_relevance contains a list with 1-4 to indicate which lines
     which contain the api info. 1 will indicate the consumer_key, 2 will indicate
     the consumer_secret, 3 will indicate access_token_key and 4 will indicate
     the access_token_secret. All 0's will be ignored.
    """
    ck = csv_content_relevance.index(1)
    cs = csv_content_relevance.index(2)
    atk = csv_content_relevance.index(3)
    ats = csv_content_relevance.index(4)
    api_info = {}
    with open(filename) as csv_file:
        lines = csv_file.readlines()
        api_info['consumer_key'] = lines[ck].rstrip()
        api_info['consumer_secret'] = lines[cs].rstrip()
        api_info['access_token_key'] = lines[atk].rstrip()
        api_info['access_token_secret'] = lines[ats].rstrip()
    return api_info


def get_source_from_csv(filename, csv_content_relevance=[1, 0, 2], delimiter=';'):
    """
    Get information to train AIManager from a csv file. The paramenter
     csv_content_relevance contains a list with 1 or 0 to indicate which
     colums to parse from csv. 1 indicates the position of the ids, 2
     indicates the position of the annotation. All 0's will be ignored.
    """
    ids_column = csv_content_relevance.index(1)
    annotation_column = csv_content_relevance.index(2)
    source_info = []
    with open(filename) as csv_file:
        for line in csv_file:
            t_id = line.split(delimiter)[ids_column]
            t_ann = int(line.split(delimiter)[annotation_column])
            source_info.append((t_id, t_ann, ))
    return source_info


class AIManager():
    def __init__(self, source_info, api_info, test_size=0.1):
        """
        Initialize and train manager. Source info must be a list of pairs (str, int)
        with the first element being a tweet id from the API and the int
        a number representing annotation.
        """
        self.api_info = api_info
        self.preprocessor = TwitterPreprocessingInSpanish(self.api_info)
        annotation_list = []
        text_list = []
        random.shuffle(source_info)
        total = len(source_info)
        print("\n\n\nBegining extraction process...")
        for i, (t_id, annotation) in enumerate(source_info):
            progress = (i+1) * 100 / total
            text_list.append(self.preprocessor.
                extract_and_clean_single(t_id, display_progress=progress))
            annotation_list.append(annotation)
        print("Extraction process completed.")
        test_size = int(len(source_info) * test_size)
        self.test_text_list = text_list[:test_size]
        self.test_annotation_list = annotation_list[:test_size]
        self.train_text_list = text_list[test_size:]
        self.train_annotation_list = annotation_list[test_size:]

        self.fe = BagOfWords(self.train_text_list, 1, 2)
        self.model = IntentionModel(self.fe.train_and_extract(
            self.train_text_list), self.train_annotation_list)
        self.model.train()

    def classify_single(self, text):
        return self.model.eval(self.fe.extract(text))

    def classify_multiple(self, text_list):
        return self.model.eval(self.fe.extract(text_list))

    def report_test_info(self):
        classes = self.model.model.classes_
        # rows will be annotations, columns will be predictions
        results = [[0 for c in classes] for c in classes]
        predictions = self.model.eval(self.fe.extract(self.test_text_list))

        for a, p in zip(self.test_annotation_list, predictions):
            results[a][p] += 1

        print(results)
        right = 0
        for c in classes:
            right += results[c][c]

        test_size = len(predictions)
        print("Correct on %.2f" % (right * 100 / test_size) + "%")

        prom = []
        for c in classes:
            print('\nFor class ' + str(c) + ':')
            p = float(results[c][c]) / (results[0][c] + results[1][c] + results[2][c])
            r = float(results[c][c]) / (results[c][0] + results[c][1] + results[c][2])
            f = 2 * ((p * r) / (p + r))
            print("Precision %.2f" % p)
            print("Recall %.2f" % r)
            print("F1-score %.2f" % f)
            prom.append(f)

        print("\navg F1-score %.2f" % (sum(prom) / 3.0))
