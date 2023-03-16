# importing libraries
import warnings

warnings.filterwarnings('ignore')
import math
import re
import warnings
from os.path import exists
from stemming.porter2 import stem
import pandas as pd
import pymongo

warnings.filterwarnings('ignore')

stop = []
pos_index = {}
track_index = []


# process csv file
def csv_parser(path):
    data = pd.read_csv(path)
    song_names = data["title"].values
    Lyrics = data["lyrics"].values
    file_map = dict(map(lambda i, j: (hash(i), preprocess(j)), song_names, Lyrics))
    mongo_file_map = dict(map(lambda i, j: (i, j), song_names, Lyrics))

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["details"]

    for i in mongo_file_map:
        mydict = {"song_name": i, "song_lyrics": mongo_file_map[i],"song_hash": hash(i)}
        x = mycol.insert_one(mydict)

    return file_map, song_names


def output_into_mongodb(pi):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["index"]

    for key in sorted(pi):
        index_songs = []
        index_location = []
        for doc_no in pi[key][1]:
            word_pos = pi[key][1][doc_no]
            real_pos = []
            for pos in word_pos:
                real_pos.append(pos + 1)
            index_songs.append(doc_no)
            index_location.append(real_pos)

        mydict = {"index_name": str(key), "index_times": str(pi[key][0]), "index_songs": index_songs,
                  "index_location": index_location}
        x = mycol.insert_one(mydict)



def stopwords(path):
    global stop
    with open(path, 'r') as f_s:
        for x in f_s:
            stop.append(x.strip())

    return stop


# tokenization, remove stopwords, lower case, stemming
def preprocess(text):
    p_words = []
    tokenization = re.sub('\W', ' ', text.lower()).split()

    for word in tokenization:
        if word not in stop:
            if stem(word).strip() != "":
                p_words.append(stem(word).strip())
    return p_words


# generate inverted index
def inverted_index(file_map):
    for key in file_map:
        wordlist = file_map[key]
        for pos, word in enumerate(wordlist):
            if word in pos_index:
                if key in pos_index[word][1]:
                    pos_index[word][1][key].append(pos)
                else:
                    pos_index[word][1][key] = [pos]
            else:
                pos_index[word] = []
                pos_index[word].append(1)
                pos_index[word].append({})
                pos_index[word][1][key] = [pos]

    for term in pos_index:
        for i in pos_index[term]:
            pos_index[term][0] = len(pos_index[term][1])

    return pos_index


# generate index file
def output_index(pi):
    filename = 'testindex.txt'
    with open(filename, 'w') as f:
        for key in sorted(pi):
            f.write(str(key) + ': ' + str(pi[key][0]) + '\n')
            for doc_no in pi[key][1]:
                word_pos = pi[key][1][doc_no]
                f.write('\t' + str(doc_no) + ': ' + ','.join(str(pos + 1) for pos in word_pos) + '\n')
            # f.write('\n')


def output_index_delta_encoding(pi):
    filename = 'index_delta1.txt'
    with open(filename, 'w') as f:
        for key in sorted(pi):
            f.write(str(key) + ': ' + str(pi[key][0]) + '\n')
            for doc_no in pi[key][1]:
                word_pos = pi[key][1][doc_no]
                f.write('\t' + str(doc_no) + ': ')
                last_pos = -1
                for v, pos in enumerate(word_pos):
                    if v == 0:
                        if len(word_pos) == 1:
                            f.write((str(pos + 1)))
                        else:
                            f.write((str(pos + 1)) + ',')
                        last_pos = pos + 1
                    elif v == len(word_pos) - 1:
                        f.write((str(pos + 1 - last_pos)))
                    else:
                        f.write((str(pos + 1 - last_pos)) + ',')
                        last_pos = pos + 1
                f.write('\n')


def output_into_mongodb(pi):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["index"]

    for key in sorted(pi):
        index_songs = []
        index_location = []
        for doc_no in pi[key][1]:
            word_pos = pi[key][1][doc_no]
            real_pos = []
            for pos in word_pos:
                real_pos.append(pos + 1)
            index_songs.append(doc_no)
            index_location.append(real_pos)

        mydict = {"index_name": str(key), "index_times": str(pi[key][0]), "index_songs": index_songs,
                  "index_location": index_location}
        x = mycol.insert_one(mydict)


def read_from_mongodb():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["index"]

    ii = {}
    for x in mycol.find():
        i = 0
        inner_dict = {}
        for song in x["index_songs"]:
            inner_dict[song] = x["index_location"][i]
            i = i + 1
        ii[x["index_name"]] = [x["index_times"], inner_dict]

    return ii

def read_from_mongodb(term):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["index"]
    myquery = {"index_name": term}

    ii = {}
    x = mycol.find_one(myquery)
    i = 0
    inner_dict = {}
    for song in x["index_songs"]:
        inner_dict[song] = x["index_location"][i]
        i = i + 1
    ii[x["index_name"]] = [x["index_times"], inner_dict]

    return ii


# generate boolean query result file
def output_results_boolean(map_result):
    filename = 'result.boolean.txt'
    with open(filename, 'w') as f:
        for key in map_result:
            map_result[key][0] = sorted(list(map(int, map_result[key][0])))
            for i in map_result[key][0]:
                f.write(str(key) + ',' + str(i) + '\n')
        f.write('\n')


# generate ranked query result file
def output_results_ranked(map_result):
    filename = 'result.ranked.txt'
    with open(filename, 'w') as f:
        for key in map_result:
            for i in map_result[key][0]:
                f.write(str(key) + ',' + str(i) + '\n')
        f.write('\n')


# process query file
def read_queries(path):
    map_result = {}
    query_list = []
    query_no_list = []
    with open(path, 'r') as f_q:
        queries = f_q.read().splitlines()
        for line in queries:
            query_no = line[: line.index(' ')]
            query_no_list.append(query_no)
            query = line[line.index(' ') + 1:]
            query_list.append(query)
    # print(query_list)

    count = 0
    for query in query_list:
        result_list = []
        if 'AND' in query or 'OR' in query:
            part_result = boolean_search(query)
        elif '"' in query:
            part_result = phrase_search(query)
        elif '#' in query:
            part_result = proximity_search(query)
        elif ' ' not in query:
            part_result = word_search(query)
        else:
            part_result = tfidf(query)
        result_list.append(part_result)
        map_result[query_no_list[count]] = sorted(result_list)
        count = count + 1

    return map_result


# single word search
def word_search(query):
    neg = False
    if 'NOT' in query:
        query = query[4:]
        neg = True

    result = []
    term = query.strip('')
    term = preprocess(term)
    index = pos_index[term[0]]

    for doc_no in index[1]:
        result.append(doc_no)

    real_result = result
    if neg:
        real_result = negative(real_result)

    real_result = sorted(list(set(real_result)))
    # print("word_search")
    # print(real_result)
    return real_result


# phrase search
def phrase_search(query):
    neg = False
    if 'NOT' in query:
        query = query[4:]
        neg = True

    result = []
    terms = query.strip('"')
    term1, term2 = terms.split(' ', 1)
    term1 = preprocess(term1)
    term2 = preprocess(term2)
    index1 = pos_index[term1[0]]
    index2 = pos_index[term2[0]]

    for doc_no1 in index1[1]:
        for doc_no2 in index2[1]:
            if doc_no1 == doc_no2:
                for pos1 in index1[1][doc_no1]:
                    for pos2 in index2[1][doc_no2]:
                        if (pos2 - pos1) == 1:
                            result.append(doc_no1)
    real_result = result
    if neg:
        real_result = negative(real_result)

    real_result = sorted(list(set(real_result)))
    # print("phase_search")
    # print(real_result)
    return real_result


# proximity search
def proximity_search(query):
    neg = False
    if 'NOT' in query:
        query = query[4:]
        neg = True

    result = []
    distance = int(query[query.index('#') + 1: query.index('(')])
    term1 = query[query.index('('): query.index(',')].strip()
    term2 = query[query.index(','): query.index(')')].strip()
    term1 = preprocess(term1)
    term2 = preprocess(term2)
    index1 = pos_index[term1[0]]
    index2 = pos_index[term2[0]]

    for doc_no1 in index1[1]:
        for doc_no2 in index2[1]:
            if doc_no1 == doc_no2:
                for pos1 in index1[1][doc_no1]:
                    for pos2 in index2[1][doc_no2]:
                        if abs((pos2 - pos1)) <= distance:
                            result.append(doc_no1)
    real_result = result
    if neg:
        real_result = negative(real_result)

    real_result = sorted(list(set(real_result)))
    # print("proximity_search")
    # print(real_result)
    return real_result


# boolean search
def boolean_search(query):
    real_result = []
    if 'AND' in query:
        terms = query.split(' AND ')
        if '"' in terms[0]:
            result1 = phrase_search(str(terms[0]))
        elif '#' in terms[0]:
            result1 = proximity_search(str(terms[0]))
        else:
            result1 = word_search(str(terms[0]))

        if '"' in terms[1]:
            result2 = phrase_search(str(terms[1]))
        elif '#' in terms[1]:
            result2 = proximity_search(str(terms[1]))
        else:
            result2 = word_search(str(terms[1]))
        real_result = sorted(list(set(result1).intersection(set(result2))))

    if 'OR' in query:
        terms = query.split(' OR ')
        term1 = preprocess(terms[0])
        term2 = preprocess(terms[1])
        if '"' in term1:
            result1 = phrase_search(str(term1[0]))
        elif '#' in term1:
            result1 = proximity_search(str(term1[0]))
        else:
            result1 = word_search(str(term1[0]))

        if '"' in term2:
            result2 = phrase_search(str(term2[0]))
        elif '#' in term2:
            result2 = proximity_search(str(term2[0]))
        else:
            result2 = word_search(str(term2[0]))
        real_result = sorted(list(set(result1).union(set(result2))))

    return real_result


# deal with NOT
def negative(result):
    real_result = track_index
    for i in result:
        real_result.remove(str(i))
    return real_result


def bm25(query, track_id, file_map):
    terms = preprocess(query)
    piterm = {}
    for term in terms:
        piterm.update(read_from_mongodb(term))
    score = {}
    l=0
    for id1 in track_id:
        l+= len(file_map[id1])
    l_ = l/len(track_id)

    for id in track_id:
        weight = 0
        ld = len(file_map[id])
        k =1.5
        for term in piterm:
            if id in piterm[term][1]:
                dl = piterm[term]
                tf_td = len(dl[1][id])
                dft = len(piterm[term][1])
                # wtd1 = ((1 + math.log10(tf_td)) * math.log10(len(song_names) / dft))

                wtd2 = (tf_td/((k*(ld/l_))+tf_td+0.5))*math.log10((len(track_id)-dft+0.5)/(dft+0.5))
                weight = weight + wtd2
        score[str(id)] = weight

    score = sorted(score.items(), key=lambda x: -x[1])
    result_list = []

    for i, (k, v) in enumerate(score):
        if i in range(0, 5):
            result_list.append(str(k) + ',' + ('%.4f' % v))

    return result_list


# ranked
def tfidf(query, track_index):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["details"]

    terms = preprocess(query)
    piterm = {}
    for term in terms:
        piterm.update(read_from_mongodb(term))

    score = {}
    for index in track_index:
        weight = 0
        for term in piterm:
            if index in piterm[term][1]:
                dl = piterm[term]
                tf_td = len(dl[1][index])
                dft = len(piterm[term][1])
                wtd = ((1 + math.log10(tf_td)) * math.log10(len(track_index) / dft))
                weight = weight + wtd
        score[str(index)] = weight

    score = sorted(score.items(), key=lambda x: -x[1])
    result_list = []

    for i, (k, v) in enumerate(score):
        if i in range(0, 5):
            myquery = {"song_hash": int(k) }
            mydoc = mycol.find_one(myquery)
            result_list.append(str(mydoc["song_name"]) + ',' + ('%.4f' % v))

    return result_list


def read_songs_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["song"]
    mycol = mydb["details"]

    for x in mycol.find():
        track_index.append(x["song_hash"])

    return track_index



def main():
    global stop
    global file_map
    stop = stopwords("englishST.txt")
    index_file = "testindex.txt"
    file_exists = exists(index_file)

    if file_exists:
        track_id = read_songs_from_db()
        print(tfidf("love", track_id))
        print(bm25("love", track_id, file_map))


    else:
        file_map, track_index = csv_parser("LyricsSmall.csv")
        ii = inverted_index(file_map)
        output_index(ii)
        output_into_mongodb(ii)
        #output_index_delta_encoding(ii)
        #pos_index = ii


if __name__ == "__main__":
    main()
