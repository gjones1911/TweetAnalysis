import csv
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import itertools
from datetime import datetime
import re
import math
import random
from itertools import repeat
import sys
import os
from gensim import utils
from gensim.models import Doc2Vec
import gensim
import numpy as np

#from medium.com (mostly)
class LabeledLineSentence(object):
	
	def __init__(self, doc_list, labels_list):
		self.labels_list = labels_list
		self.doc_list = doc_list

	def __iter__(self):
		for t, l in itertools.izip(self.doc_list, self.labels_list):
			yield gensim.models.doc2vec.LabeledSentence(t, [l])


tweets = []
labels_list = []

tweetlabel_dict = {}

#reading in training data
for dirs, subdirs, files in os.walk("training_data/supervised_data"):  #all data for supervised learning should be put in this directory
	for fname in files:
		file = open(dirs + "/" + fname, "r")
		csv_read = csv.reader(file)
		header = csv_read.next()
		for row in csv_read:
			if row[1] != '': #try to keep tweet as first entry and label as second
				label = row[1]
				if '.' in label: #get rid of decimal labeling if there is any
					label = re.match(r'^(.*?)\..*', label).group(1)
				label = int(label)
				tweet = row[0]
				if label != 17: #ignore label 17 ('not sure')
					#put into dictionary so we can count the tweets per label
					if label not in tweetlabel_dict:
						tweetlabel_dict[label] = [tweet]
					else:
						tweetlabel_dict[label].append(tweet)

tweets = []
labels_list = []

#balancing out the training data (~500 in each category)
for k, v in tweetlabel_dict.iteritems():
	
	if len(v) > 500:
		sample = random.sample(v, 500)
		for s in sample:
			tweets.append(s)
		labels_list.extend(repeat(k, 500))

	elif len(v) < 500:
		iters = math.ceil(500.0/len(v))
		for i in range (0, int(iters)):
			for vals in v:
				tweets.append(vals)
				labels_list.append(k)

training_data = LabeledLineSentence(tweets, labels_list)
	
	
#build the doc2vec model
model = Doc2Vec(vector_size=300, alpha=0.025, min_alpha=0.00025, min_count=0, dm=1)
model.build_vocab(training_data)
for epoch in range(10):
	model.train(training_data, total_examples=model.corpus_count, epochs=model.epochs)
	model.alpha -= 0.0002
	model.min_alpha = model.alpha


#put tweets into classifier
train_tweets = []

for i in range(len(tweets)):
	label = labels_list[i]
	train_tweets.append(model[label])

#have to convert to numpy array because that is what clf takes
train_tweets = np.array(train_tweets)
train_labels = np.array(labels_list)

clf = RandomForestClassifier().fit(train_tweets, train_labels)


#get the test data from the dataset of tweets
test_data = []

typeoffile = sys.argv[1] #media or utility
file_name = 'dates'
if typeoffile == 'media':
	file_name = 'm_dates'

#open test data obtained from media/utility file, parse
file = open("training_data/" + file_name + ".txt", "r")
w = file.read()
test = w.split("\t")
for t in test:
	if t != '\n':
		t = t.split('~+&$!sep779++')
		if t != ['']:
			if t[1]:
				t[1] = t[1].strip()
				date = ''
				if '/' in t[1]:
					date = datetime.strptime(t[1], '%m/%d/%Y')
				elif '-' in t[1]:
					date = datetime.strptime(t[1], '%Y-%m-%d')
				#make sure only data from september is included
				start = datetime(year=2017, month=9, day=1)
				end = datetime(year=2017, month=9, day=30)
				if start < date < end:
					test_data.append([t[0], date, t[2]])


#open predictions file for writing
outfile = open("results/" + typeoffile + "_supervised_rf_doc2vec.csv", "w")
writer = csv.writer(outfile)
writer.writerow(['Tweet', 'Category', 'Date', 'Permalink'])

count_vect = CountVectorizer()

#make prediction for each tweet, write to file
for t in test_data:
	vect = count_vect.transform([t[0]])
	prediction = clf.predict(t[0])
	#writing tweet, prediction, date, and permalink
	writer.writerow([t[0], int(prediction), t[1].strftime('%m/%d/%Y'), t[2]])
	
