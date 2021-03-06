from flask import Flask, render_template, Response, request
import cv2
import datetime, time
import os
from threading import Thread
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from flask_ngrok import run_with_ngrok


# Defining global variables
global capture, rec_frame, switch, face, rec, out
capture, face, switch, rec = 0, 0, 1, 0


# Make a Capture folder to store captured images
try:
    os.mkdir('./capture')
except OSError as error:
    pass

# Load pretrained face detection model
face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Initialize flask app
app = Flask(__name__, template_folder='./templates')

camera = cv2.VideoCapture(0)

# Initializing and training the Chat
engage_bot = ChatBot("Chatterbot", storage_adapter="chatterbot.storage.SQLStorageAdapter")
trainer = ChatterBotCorpusTrainer(engage_bot)
trainer.train("chatterbot.corpus.english")


def record(out):
    global rec_frame
    while rec:
        time.sleep(0.05)
        out.write(rec_frame)


def detect_face(frame):
    global net
    frame_grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_detector.detectMultiScale(frame_grayscale)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (100, 200, 50), 4)

        the_face = frame[y:y + h, x:x + w]

        face_grayscale = cv2.cvtColor(the_face, cv2.COLOR_BGR2GRAY)

        smiles = smile_detector.detectMultiScale(face_grayscale, scaleFactor=1.7, minNeighbors=20)

        if len(smiles) > 0:
            cv2.putText(frame, 'nice, you are smiling', (x, y + h + 40), fontScale=1, fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                        color=(255, 0, 255))

    return frame


# generate frame by frame from camera
def gen_frames():
    global out, capture, rec_frame
    while True:
        success, frame = camera.read()
        if success:
            if face:
                frame = detect_face(frame)
            if capture:
                capture = 0
                now = datetime.datetime.now()
                p = os.path.sep.join(['capture', "capture_{}.png".format(str(now).replace(":", ''))])
                cv2.imwrite(p, frame)

            if rec:
                rec_frame = frame
                frame = cv2.putText(cv2.flip(frame, 1), "Recording started", (0, 25), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 0, 255), 4)
                frame = cv2.flip(frame, 1)

            try:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass

        else:
            pass


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route("/smiledec")
def smiledec():
    return render_template('smiledec.html')


@app.route("/chat")
def chat():
    return render_template('chat.html')


# Chat Bot
@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    return str(engage_bot.get_response(userText))


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/requests', methods=['POST', 'GET'])
def tasks():
    global switch, camera
    if request.method == 'POST':
        if request.form.get('click') == 'Capture':
            global capture
            capture = 1
        elif request.form.get('face') == 'Smile':
            global face
            face = not face
            if face:
                time.sleep(4)
        elif request.form.get('stop') == 'Stop/Start Video':

            if switch == 1:
                switch = 0
                camera.release()
                cv2.destroyAllWindows()

            else:
                camera = cv2.VideoCapture(0)
                switch = 1
        elif request.form.get('rec') == 'Start/Stop Recording':
            global rec, out
            rec = not rec
            if rec:
                now = datetime.datetime.now()
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                out = cv2.VideoWriter('vid_{}.avi'.format(str(now).replace(":", '')), fourcc, 20.0, (640, 480))

                # New thread to record the video
                thread = Thread(target=record, args=[out, ])
                thread.start()
            elif rec == False:
                out.release()

    elif request.method == 'GET':
        return render_template('smiledec.html')
    return render_template('smiledec.html')


if __name__ == '__main__':
    app.run(debug=True)

camera.release()
cv2.destroyAllWindows()
