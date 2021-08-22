import yaml
import os
import sys
import arxiv
import json
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def load_config_file():
    """ Loads the content of the configuration file "arxiv-notification-config.yml"
    """
    configpath = os.path.join(os.path.dirname(__file__),"arxiv-notification-config.yml")
    configfile = open(configpath, "r")
    cfg = yaml.safe_load(configfile)
    configfile.close()
    return cfg

def current_time_as_string():
    """Returns the current UTC time as string
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%m-%d-%y %H:%M:%S %z")

def load_internal_data_file():
    """ Load the internal data from "arxiv-notification-data.json". This file
        should store a dictionary with the fields:
            last_query_time: The last time this script was run
            found_ids: All arxiv ids matching the search query that have ever 
                       been found by this script
                      
        If the file does not exist, the following default values are returned:
            last_query_time: [The current time]
            found_ids: []
    """
    datapath = os.path.join(os.path.dirname(__file__),"arxiv-notification-data.json")
    if os.path.exists(datapath):
        datafile = open(datapath, 'r')
        data = json.load(datafile)
        datafile.close()
        return data
    else:
        data = {'last_query_time': current_time_as_string(),
                'found_ids': []}
        return data

def write_internal_data_file(data):
    """Writes data to "arxiv-notification-data.json"
    """
    datapath = os.path.join(os.path.dirname(__file__),"arxiv-notification-data.json")
    f = open(datapath, 'w')
    json.dump(data, f)
    f.close()

def paper_to_string(paper, html=False):
    """Returns the paper as a string to be written in the results textfile or
        in the email. Contains the name of the paper, the authors, the time
        of the submission and of the last update, and the abstract. If html=True
        bold and italicized fonts will be used for formatting"""
    res = ""
    if html:
        res+= "<p><b>"+paper.title+"</b></p>"
        res+="<p><i>"
        for (i, auth) in enumerate(paper.authors):
            res+= str(auth)
            if i!=len(paper.authors)-1:
                res+=", "
        res += "</i></p>"
        res+="<p>Submitted: "+str(paper.published.strftime("%d.%m.%y"))
        res+= ", Last Updated: "+str(paper.updated.strftime("%d.%m.%y"))+"</p>"
        res+="<p><a href={}>{}</a></p>".format(paper.entry_id, paper.entry_id)
        res += "<p>"+paper.summary+"<br><br></p>"
    else:
        res += paper.title+"\n"
        res += "------------------------------------------------------\n"
        for (i, auth) in enumerate(paper.authors):
            res+= str(auth)
            if i!=len(paper.authors)-1:
                res+=", "
        res+="\n"
        res+="Submitted: "+str(paper.published.strftime("%d.%m.%y"))
        res+= ", Last Updated: "+str(paper.updated.strftime("%d.%m.%y"))+"\n"
        res+=paper.entry_id+"\n"
        res+="\n"+paper.summary+"\n\n\n"
    return res

def send_email(message, cfg):
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL(cfg["smtp_server"], 465, context = context)
    server.login(cfg["smtp_login"], cfg["smtp_pwd"])
    server.sendmail(cfg["from_email"], cfg["to_email"], message)
    server.close()
        
def run():
    """Runs the script"""
    cfg = load_config_file()
    data = load_internal_data_file()
    
    if len(sys.argv) == 2:  #Number of days before now to be searched supplied manually
        days_before_now = int(sys.argv[1])
        now = datetime.datetime.now(datetime.timezone.utc)
        start_search_time = now - datetime.timedelta(days = days_before_now)
    else:   #Search for new papers since the script was last run
        last_query_time = datetime.datetime.strptime(data["last_query_time"], "%m-%d-%y %H:%M:%S %z")
        start_search_time = last_query_time - datetime.timedelta(days = cfg['search_days_before_last_query'])
    
    # Use the arXiv package to search for papers matching the query    
    search = arxiv.Search(query = cfg['arxiv_query'],
                          sort_by = arxiv.SortCriterion.LastUpdatedDate)
    
    # Filter papers that are newer then start_search_time and that we have not
    # seen before
    new_papers = []       #arXiv ids that we have never seen before
    updated_papers = []   #arXiv ids that we haves seen before, but in a different version
    
    found_ids_without_version = [id[:-2] for id in data['found_ids']]
    for result in search.results():
        if result.updated < start_search_time:
            break
        id = result.entry_id
        id_without_version = id[:-2]
        if not id_without_version in found_ids_without_version:
            new_papers.append(result)
            data["found_ids"].append(id)
        elif not id in data["found_ids"]:
            updated_papers.append(result)
            data["found_ids"].append(id)
      
    #Update internal data file
    data['last_query_time'] = current_time_as_string()
    write_internal_data_file(data)
     
    if len(new_papers) > 0 or len(updated_papers)>0 and cfg['notify_on_updated_papers']:
        
        #Write results to textfile
        if cfg['write_results_to_file']:
            previous_results = ""
            if os.path.exists(cfg['results_filename']):
                f = open(cfg['results_filename'],'r')
                previous_results =  f.read()
                f.close()
            new_results =  "====================================================================\n"
            new_results += "                " + current_time_as_string()+"                   \n"
            new_results += "====================================================================\n"
            if len(new_papers) > 0:
                new_results += "New Papers ({}): \n\n".format(len(new_papers))
                for paper in new_papers:
                    new_results+=paper_to_string(paper)
            if len(updated_papers)>0 and cfg['notify_on_updated_papers']:
                new_results += "Updated Papers ({}): \n\n".format(len(updated_papers))
                for paper in updated_papers:
                    new_results+=paper_to_string(paper)
            f = open(cfg['results_filename'], "w")
            f.write(new_results+previous_results)
            f.close()
            
        # Send results as email
        if cfg['send_results_as_email']:
            message = MIMEMultipart("alternative")
            message["Subject"] = "ArXiv Update {}: {} new paper(s)".format(\
                                    datetime.datetime.now().strftime("%d.%m.%y"), len(new_papers)+len(updated_papers))
            message["From"] = cfg["from_email"]
            message["To"] = cfg["to_email"]
            msg_html = "<html><body>"
            if len(new_papers) > 0:
                msg_html+="<p>New Papers({}): </p>".format(len(new_papers))
                for paper in new_papers:
                    msg_html+=paper_to_string(paper, html=True)
                
            if len(updated_papers)>0 and cfg['notify_on_updated_papers']:
                msg_html+="<p>Updated Papers({}): </p>".format(len(updated_papers))
                for paper in updated_papers:
                    msg_html+=paper_to_string(paper, html=True)
            msg_html+="</body></html>"
            message.attach(MIMEText(msg_html, "html"))
            send_email(message.as_string(),cfg)

run()
