## ====================================================   /     Packages required    /   ================================================= #

# [Youtube API libraries]
#CREATING PARAMETERS FOR THE SYNTAX
#For the ACTIVATION of resource we need Two parameters ( youtube , channel_ID ) and googlapiclient python library
from googleapiclient.discovery import build
import streamlit as st
# [SQL libraries]
import mysql.connector
# [pandas]
import pandas as pd
#Data visualizaion Libraries
import seaborn as sns
import matplotlib.pyplot as plt
from PIL import Image
#Date and Time Libraries
from datetime import datetime,timedelta
import json

## ====================================================   /     API connection    /   ================================================= #

#This build connects youtube data and api key as one parameter
def Api_connect():
    api_key = "AIzaSyAw_O0FoYWA1FXqko0ZyAhFf1cPL7S2Y4I"
    api_service_name = "youtube"
    api_version = "v3"

    youtube = build(api_service_name, api_version, developerKey=api_key)
    return youtube

utube_call = Api_connect()

## ====================================================   /     SQL connection    /   ================================================= #
mydb=mysql.connector.connect(host="127.0.0.1",user="root",password="kanis0111",database="youtube")
cursor=mydb.cursor()

## ====================================================   /     Get Channel Information     /   ================================================= #

#To get data of channel using channel id , we can use key itration to get data like this
def Channel_Info(channel_id):

    cursor.execute("""CREATE TABLE IF NOT EXISTS channel_info (
                        channel_name VARCHAR(255),
                        channel_id VARCHAR(255) PRIMARY KEY,
                        subscribe INT,
                        views INT,
                        total_videos INT,
                        channel_description TEXT,
                        playlist_id VARCHAR(255)
                    )""")
    
    request = utube_call.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()
    
    for item in response.get('items',[]):
        details = dict(Channel_Name= item['snippet']['title'],
            Channel_Id= item['id'],
            Subscribers= item['statistics']['subscriberCount'],
            Views= item['statistics']['viewCount'],
            Total_Videos= item['statistics']['videoCount'],
            Channel_Description= item['snippet']['description'],
            Playlist_Id=item['contentDetails']['relatedPlaylists']['uploads']
        )
    
        cursor.execute("INSERT INTO channel_info (channel_name, channel_id, subscribe, views, total_videos, channel_description, playlist_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (details['Channel_Name'], details['Channel_Id'], details['Subscribers'], details['Views'], details['Total_Videos'], details['Channel_Description'], details['Playlist_Id']))
        
        mydb.commit()
    return details

#Get Video Id
#We no having the channel information including PLAYLIST_ID , this will help us to get all VIDEO_ID's of channel to fetch all video data
def Get_Video_Id(video_id):
    Video_ID=[]
    response=utube_call.channels().list(id=video_id,
                                    part='contentDetails').execute()

    Playlist_ID=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    Next_Page_Token=None

    while True:
        request_1=utube_call.playlistItems().list(
                                                part='snippet',
                                                playlistId=Playlist_ID,
                                                maxResults=50,
                                                pageToken=Next_Page_Token).execute()
        for i in range(len(request_1['items'])):
            Video_ID.append(request_1['items'][i]['snippet']['resourceId']['videoId'])
        Next_Page_Token=request_1.get('nextPageToken')

        if Next_Page_Token is None:
            break
    
    return Video_ID


#Get Video Details
def parse_duration(duration_str):
    try:
        duration_seconds = int(duration_str[2:-1])
        return duration_seconds
    except ValueError:
        return None

def Get_Video_Details(Video_id):
    Video_List = []
    for v_id in Video_id:
        request = utube_call.videos().list(
            part="snippet,contentDetails,statistics",
            id=v_id
        )
        response = request.execute()

        cursor.execute("""CREATE TABLE IF NOT EXISTS video_details(
                    channel_name VARCHAR(255),
                    channel_id VARCHAR(255) ,
                    video_id VARCHAR(255) PRIMARY KEY ,
                    title TEXT,
                    tags TEXT,
                    thumbnail TEXT,
                    description TEXT,
                    published_date DATETIME,
                    duration TIME,
                    views BIGINT,
                    likes INT,
                    dislikes INT,
                    comments INT
                )"""
                        )

        for item in response['items']:
            Data = dict(
                channel_Name=item['snippet']['channelTitle'],
                Channel_Id= item['snippet']['channelId'],
                Video_Id= item['id'],
                Title= item['snippet']['title'],
                Tags= json.dumps(item.get('tags')),
                Thumbnail=json.dumps(item['snippet']['thumbnails']),
                Description=item['snippet'].get('description', ''),
                Publish_Date= item['snippet']['publishedAt'],
                Duration=item['contentDetails']['duration'],
                Views=item['statistics'].get('viewCount', 0),
                Likes= item['statistics'].get('likeCount', 0),
                Dislikes=item['statistics'].get('dislikeCount'),
                Comments= item['statistics'].get('commentCount', 0)
                )
            
            Video_List.append(Data)

            duration_seconds = parse_duration(Data['Duration'])
            if duration_seconds is not None:
                duration = timedelta(seconds=duration_seconds)
            else:
                duration = timedelta(seconds=0) 
            current_datetime = datetime.now()
            updated_datetime = current_datetime + duration
            sql_duration = updated_datetime.strftime('%Y-%m-%d %H:%M:%S')

            iso_datetime = Data['Publish_Date']
            parsed_datetime = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
            mysql_published_date = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("INSERT INTO video_details(channel_name, channel_id, video_id, title ,tags ,thumbnail , description, published_date, duration, views, likes, dislikes, comments) VALUES (%s, %s, %s, %s, %s, %s,  %s, %s, %s, %s,%s,%s,%s)",
                (Data['channel_Name'], Data['Channel_Id'], Data['Video_Id'],Data['Title'],Data['Tags'], Data['Thumbnail'], Data['Description'],mysql_published_date, sql_duration, Data['Views'], Data['Likes'], Data['Dislikes'], Data['Comments']))

        mydb.commit()        
    return Video_List

#Get Comment Details
def get_comment_Details(get_Comment):
    comment_List=[]
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS comment_details (
                            comment_id VARCHAR(255) PRIMARY KEY ,
                            video_id VARCHAR(255)  ,
                            comment_text TEXT,
                            author VARCHAR(255),
                            published_date DATETIME
                        )""")
        for Com_Det in get_Comment:
            request=utube_call.commentThreads().list(
                part="snippet",
                videoId=Com_Det,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                    Comment_Det=dict(Comment_ID=item['snippet']['topLevelComment']['id'],
                                    Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                                    Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                                    Author_Name=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                                    Published_Date=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                    
                    comment_List.append(Comment_Det)

                    iso_datetime = Comment_Det['Published_Date']
                    parsed_datetime = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
                    mysql_published_dates = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')

                    cursor.execute("INSERT INTO comment_details (comment_id, video_id, comment_text, author, published_date) VALUES (%s, %s, %s, %s,%s)",
                                (Comment_Det['Comment_ID'], Comment_Det['Video_Id'], Comment_Det['Comment_Text'], Comment_Det['Author_Name'],mysql_published_dates))
                    mydb.commit()
                    
    except Exception as e:
        print(f"Error: {e}")
        
    return comment_List

#get_playlist_details
def get_playlist_details(channel_id):
    Playlist_Data=[]
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS playlist_details (
                            playlist_id VARCHAR(255),
                            title VARCHAR(255),
                            channel_id VARCHAR(255),
                            published_date DATETIME,
                            video_count INT
                        )""")
        Next_Page_Token=None

        while True:
            request=utube_call.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=Next_Page_Token
        )
            response=request.execute()

            for item in response['items']:
                PlayList_Det=dict(Playlist_Id=item['id'],
                            Title= item['snippet']['title'],
                            Channel_Id=item['snippet']['channelId'],
                            Published_Date=item['snippet']['publishedAt'],
                            Video_Count=item['contentDetails']['itemCount']
                            )
            Playlist_Data.append(PlayList_Det)

            Next_Page_Token=response.get('nextPageToken')
            if Next_Page_Token is None:
                break

        iso_datetime = PlayList_Det['Published_Date']
        parsed_datetime = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        mysql_published_datee = parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Insert data into MySQL
        cursor.execute("INSERT INTO playlist_details (playlist_id, title, channel_id, published_date, video_count) VALUES (%s, %s, %s, %s, %s)",
        (PlayList_Det['Playlist_Id'], PlayList_Det['Title'], PlayList_Det['Channel_Id'], mysql_published_datee, PlayList_Det['Video_Count']))
        mydb.commit()
    except Exception as e:
        print(f"Error: {e}")

    return Playlist_Data

#Overall Function get details
def fetch_all_data(channel_id):
    channel_info = Channel_Info(channel_id)
    video_id=Get_Video_Id(channel_id)
    playlist_details = get_playlist_details(channel_id)
    video_details = Get_Video_Details(video_id)
    comment_details = get_comment_Details(video_id)

# Convert dict to DataFrames
    channel_df = pd.DataFrame([channel_info])
    video_df = pd.DataFrame(video_id)
    playlist_df = pd.DataFrame(playlist_details)
    video_detail_df = pd.DataFrame(video_details)
    comment_df = pd.DataFrame(comment_details)
    
    return {
        "channel_details": channel_df,
        "video_details": video_df,
        "comment_details": comment_df,
        "playlist_details": playlist_df,
        "video_data": video_detail_df
    }
## ====================================================   /     SETTING PAGE CONFIGURATIONS     /   ================================================= #
   
#Streamlit's Execution model makes it easy to turn the scripts into  interactive we applicaions

def main():
    #Elements can be passed to st.sidebar using object notation and with notation.      
    st.sidebar.header(':red[MENU]')
    option=st.sidebar.radio(":black[Select option]",['DataCollection','Analysis Using MYSQL'])
    st.image('logo.png',width=200)
    with st.sidebar:
        st.write("\n")
        st.write("\n")
        st.write("\n")
        st.write("\n")
        st.write("\n")
        st.write("\n")
        st.write("\n")
        st.write(":blue[ :woman-raising-hand: Greeting to all. I am Kanimozhi Sureskumar.I would like to share my first Data Science project with  all.]")
        st.write("\n")
        st.write(":blue[The project was given by]")
        st.write(":blue[GUVI Geek Networks]")
        st.write(":blue[IITM Research Park, GUVI]")

    if option=="DataCollection":
            st.subheader(':globe_with_meridians: :red[YouTube Data Harvesting and Warehousing using SQL and Streamlit]:globe_with_meridians:', divider= 'rainbow')       
            st.subheader(':red[Domain :triangular_flag_on_post:]')
            st.markdown(':green[Social Mdeia]')
            st.write('\n')
            st.subheader(':red[SKILLS TAKE AWAY :triangular_flag_on_post:]')
            st.markdown(':green[Python Scripting]')
            st.markdown(':green[Pandas DataFrame]')
            st.markdown(':green[Data Extraction]')
            st.markdown(':green[Youtube API Integration]')
            st.markdown(':green[Streamlit Web Application]')
            st.markdown(':green[Data Management using MySQL]')           
            st.write('\n')
            st.write('-----')
            st.subheader(':inbox_tray: :blue[Data Collection Zone]')
            st.write ('(Note:- This zone **collect data** by using channel id and **stored it in the :green[MYSQL] database**.)')

            
            channel_id = st.text_input("Enter Channel ID")
            st.write('''Get data and stored it in the MYSQL database to click below **:blue['Enter Channel ID']**.''')
            
            if st.button("Get Channel Details"):
                details = fetch_all_data(channel_id)
                
                st.subheader('Channel Details')
                st.write(details["channel_details"])
                

                st.subheader('Video Details')
                st.write(details["video_data"])

                st.subheader('Comment Details')
                st.write(details["comment_details"])

                st.subheader('Playlist Details')
                st.write(details["playlist_details"])
              
            
    elif option == "Analysis Using MYSQL":
        st.header(":violet[Data Migrate zone]")
        st.write ('''(Note:- This zone specific channel data *Migrate to :blue[MySQL] database* depending on your selection,
                if unavailable your option first collect data.)''')
#it can be use SQL queries to join the tables in the SQL data warehouse and retrieve data for specific channels based on user input.
        questions = [
                    "1. What are the names of all the videos and their corresponding channels?",
                    "2. Which channels have the most number of videos, and how many videos do they have?",
                    "3. What are the top 10 most viewed videos and their respective channels?",
                    "4. How many comments were made on each video, and what are their corresponding video names?",
                    "5. Which videos have the highest number of likes, and what are their corresponding channel names?",
                    "6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?",
                    "7. What is the total number of views for each channel, and what are their corresponding channel names?",
                    "8. What are the names of all the channels that have published videos in the year 2022?",
                    "9. What is the average duration of all videos in each channel, and what are their corresponding channel names?",
                    "10. Which videos have the highest number of comments, and what are their corresponding channel names?"
                    ]

        selected_questions = st.multiselect("Select questions to execute", questions)
        if st.button("Run Selected Queries"):

            for selected_question in selected_questions:
        
                if selected_question == questions[0]:
                    cursor.execute("SELECT channel_name,title FROM video_details")
                    data = cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel Name', 'Title'])
                    st.write(df)              
                    st.bar_chart(data=df)
                    st.balloons()
                                           
                elif selected_question == questions[1]:
                    cursor.execute("SELECT channel_name, COUNT(*) as video_count FROM video_details GROUP BY channel_name ORDER BY video_count DESC")
                    data=cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel Name', 'Counts'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()
#choose different columns to use for x(Channel_name) and y(title), as well as set the color dynamically based on the column (assuming your dataframe is in long format):
#The “bar_chart()” method of Streamlit can display histograms  

                    
                elif selected_question == questions[2]:
                    cursor.execute("SELECT channel_name,title,views FROM video_details ORDER BY views DESC LIMIT 10")
                    data=cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel Name', 'Title', 'Views'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[3]:
                    cursor.execute("SELECT title,comments FROM video_details")
                    data=cursor.fetchall()
                    df=df=pd.DataFrame(data, columns=['Title','Comments'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[4]:
                    cursor.execute("SELECT channel_name,MAX(likes) as max_likes FROM video_details GROUP BY channel_name")
                    data=cursor.fetchall()
                    df=pd.DataFrame(data, columns=['Channel_Name','Likes'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[5]:
                    cursor.execute("SELECT title, SUM(likes) as total_likes, SUM(dislikes) as total_dislikes FROM video_details GROUP BY title")
                    data=cursor.fetchall()
                    df=pd.DataFrame(data, columns=['Title','Likes','Dislikes'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[6]:
                    cursor.execute("SELECT channel_name, SUM(views) as total_views FROM video_details GROUP BY channel_name")
                    data=cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel_Name', 'Views'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[7]:
                    cursor.execute("SELECT DISTINCT channel_name FROM video_details WHERE YEAR(published_date) = 2022;")
                    data=cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel_Name'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[8]:
                    cursor.execute("SELECT channel_name, AVG(duration) AS avg_duration FROM video_details GROUP BY channel_name ")
                    data=cursor.fetchall()
                    df = pd.DataFrame(data, columns=['Channel_Name', 'Avg_Duration'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()

                elif selected_question == questions[9]:
                    cursor.execute("""SELECT title, channel_name, SUM(comments) as comments
                            FROM video_details 
                            GROUP BY title, channel_name 
                            ORDER BY comments DESC 
                            LIMIT 1
                        """)
                    data = cursor.fetchall()
                    df=pd.DataFrame(data,columns=['Title','Channel_Name','Comments'])
                    st.write(df)
                    st.bar_chart(data=df)
                    st.balloons()
   
       
if __name__ == "__main__":
    main()
## ====================================================   /     End zone     /   ================================================= #


