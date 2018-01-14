import requests
import sys
import os
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash, json, jsonify




app = Flask(__name__)

username = os.environ.get('USERNAME', None)
password = os.environ.get('PASSWORD', None)
environment_id = os.environ.get('ENVIRONMENT_ID', None)
collection_id = os.environ.get('COLLECTION_ID', None)
endpoint = "https://gateway.watsonplatform.net/discovery/api/v1/environments/"+environment_id+"/collections/"+collection_id+"/query?version=2017-11-07&"

@app.route('/')
def error():
    
    return "Please specify a search term in your URL"

@app.route('/newHeadlines', methods=['POST'])
def newHeadlines():
    combo = request.json['combo']
    comboWords=combo.replace("\"","").split('|')

    combos=[]
    headlines={}
    
    
    try:
        get_url = endpoint+"query=title:("+combo+")|enrichedTitle.entities.text:("+combo+")&count=50&return=title,url"
        results = requests.get(url=get_url, auth=(username, password)) 
        response = results.json()

    
        for article in response['results']:
            combos[:]=[]
            for word in comboWords:
                if word.upper() in article['title'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][article['title']]=article['url']

            
    except Exception as e:
        print e
    output = { 'headlines': headlines }  
    return jsonify(output)

@app.route('/click', methods=['GET', 'POST'])
def click():
   
    
    nodes=request.json['nodes']
    links=request.json['links']
    bigWords=request.json['bigWords']
    index=request.json['current']
    
    x = nodes[index]['x']
    y = nodes[index]['y']
    text = nodes[index]['text']

    length = len(nodes)
    words={}
    headlines={}
    combo=""
    comboWords=[]
    combos=[]
    for node in nodes:
        words[node['text']] = node['index']
        if node['expand'] == 1:
            comboWords.append(node['text'])
    for word in comboWords:
        combo+="\""+word+"\"|"
    combo=combo[:-1]

    try:
        get_url = endpoint+"query=text:("+combo+")|enriched_text.entities.text:("+combo+")" + "&deduplicate=false&highlight=true&passages=true&passages.count=50&passages.characters=1000"+"&count=50&return=title,url"
        results = requests.get(url=get_url, auth=(username, password)) 
        response = results.json()

        print "OnClick"
        print get_url
        print len(response['passages'])

        ##Populate the passages content in the right hand side
    
        for passage in response['passages']:
            combos[:]=[]
            for word in comboWords:
                if word.upper() in passage['passage_text'].upper():
                    combos.append(word)
            comboStr = ''.join(sorted(combos))
            comboLen = len(combos)
            if comboLen not in headlines:
                headlines[comboLen]={}
            if comboStr not in headlines[comboLen]:
                headlines[comboLen][comboStr]={}
            headlines[comboLen][comboStr][passage['passage_text']]=passage['document_id']

    except Exception as e:
        print e
    
    output = { 'results': { 'nodes': [], 'links': [], 'headlines': headlines, 'combo': combo } }
 

    try:
        #get_url = endpoint+"query=text:\""+text+"\"&aggregation=nested(enriched_text.entities).filter(enriched_text.entities.type:Person).term(enriched_text.entities.text,count:100)&count=0"
        get_url = endpoint+"query=text:\""+text+"\"&aggregation=nested(enriched_text.concepts).term(enriched_text.concepts.text,count:100)&count=0"
        results = requests.get(url=get_url, auth=(username, password)) 
        response=results.json()
        
        #add to bigWords
        wordList = []
        for kword in response['aggregations'][0]['aggregations'][0]['results']:
            wordList.append(kword['key'])
        bigWords[text]={'wordList':wordList,'expand':1}  
        output['results']['bigWords']=bigWords    
        count1=0 
        count2=0

        for newWord in bigWords[text]['wordList']:
            if newWord in words:
                    output['results']['links'].append({'source':index,'target':words[newWord]})
                    continue
            if count2 < 5:    
                for bigWord in bigWords:
                    if bigWords[bigWord]['expand']==0:
                        continue
                    if bigWord == text:
                        continue
                    if newWord in bigWords[bigWord]['wordList']:
                        if newWord not in words:
                            output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})
                            words[newWord]=length
                            length+=1
                            count2+=1
                        output['results']['links'].append({'source':words[newWord],'target':words[bigWord]})
                        output['results']['links'].append({'source':words[newWord],'target':index})
            if newWord not in words and count1 < 5:
                output['results']['nodes'].append({'x': x, 'y': y, 'text': newWord, 'size': 1.5, 'color': 'white', 'expand': 0})   
                output['results']['links'].append({'source':length,'target':index})
                length+=1
                count1+=1
                    
    except Exception as e:
        print e 
                
    return jsonify(output)

@app.route('/favicon.ico')
def favicon():
   return ""


@app.route('/<keyword>')
def news_page(keyword):
    index=0
    nodes=[]
    links=[]
    headlines={}
    headlines[1]={}
    headlines[1][keyword]={}
    
    bigWords={}
    
    try:
        get_url = endpoint+"query=natural_language_query="+keyword+"&deduplicate=false&highlight=true&passages=true&passages.count=50&passages.characters=1000"+"&count=50&return=title,url"
        results = requests.get(url=get_url, auth=(username, password)) 
        response = results.json()
    
        #Thiz is used to populate the lis in the right hand side
        print "Passages:"
        #print response['passages']
        
        for passage in response['passages']:
            headlines[1][keyword][passage['passage_text']]=passage['document_id'] 
        
        
        print len(headlines)
        print json.dumps(headlines)

    except Exception as e:
        print e
 
    try:
        get_url = endpoint+"natural_language_query="+keyword+ "&aggregation=nested(enriched_text.entities).filter(enriched_text.entities.type:Person).term(enriched_text.entities.text,count:100)&count=0"
        #get_url ="https://gateway.watsonplatform.net/discovery/api/v1/environments/106d1355-1bab-4e85-9e20-5bfe6b8820d7/collections/86c0f704-69d8-49df-9a67-686a5c5651e0/query?version=2017-11-07&deduplicate=false&highlight=true&passages=true&passages.count=5&natural_language_query="+keyword
        results = requests.get(url=get_url, auth=(username, password)) 
        response=results.json()

        print "start extracting keywords"
        print response
        print len(response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results'])

        #add to bigWords
        wordList = []
        for kword in response['aggregations'][0]['aggregations'][0]['aggregations'][0]['results']:
            wordList.append(kword['key'])
        bigWords[keyword]={'wordList':wordList,'expand':1}   
        print "Got big words" 
        print len(wordList)

    except Exception as e:
        print("Got Error when getting bigwords")
        print e
 

    print "Getting data to screen"
    print len(bigWords[keyword]['wordList'])
    
    count=0
    nodes.insert(0, {'x': 300, 'y': 200, 'text': keyword, 'size': 3, 'fixed': 1, 'color': '#0066FF', 'expand': 1})
    for word in bigWords[keyword]['wordList']:
        #if count > 14:
        #    break
        if word == keyword:
            continue
        else:
            nodes.append({'x': 300, 'y': 200, 'text': word, 'size': 1.5, 'color': 'white', 'expand': 0})
            links.append({'source':count + 1,'target':0})
            count+=1
                   
    return render_template('cloud.html', nodes=json.dumps(nodes), links=json.dumps(links), bigWords=json.dumps(bigWords), headlines=json.dumps(headlines))

port = os.getenv('VCAP_APP_PORT', '8000')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(port), debug=True)

