from flask import Flask, render_template, request
from flaskext.mysql import MySQL
import boto3
import os

app = Flask(__name__)

# connection to database
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'faceanalyze'

# initialized for connection
mysql = MySQL(app)

# awsconfiguration
app.secret_key = 'your_secret_key'
bucket_name = "genesefaceanalysis"

# extracting s3 api
s3 = boto3.client("s3", aws_access_key_id='acess_key_id',
aws_secret_access_key='access_key',
aws_session_token='session_token')
bucket_resource = s3

# extracting api for rekognition
client = boto3.client("rekognition", aws_access_key_id='acess_key_id',
aws_secret_access_key='access_key',
aws_session_token='session_token')



@app.route("/")
def home():
    """
        Loading base webpage from templates
    """
    return render_template("index.html")


@app.route('/analyze', methods=['POST'])
def analyze():
    """
        Takes in the input photo from client and
        uses AWS Rekognition API to analyze the face.
            Returns
                ----------
                gender(string): the gender of the person in the image
                agerange(string) : the age range of the person in the image
                eye(string) : returns if the image has eyeglasses on
                sun (string) : returns if the image has sunglasses on
                mus(string): returns if the face
                            detected has moustache or beard.
            Renders
                ------------
                index.html(page): Returns to the base webpage

        """
    output = []
    attributes = []
    file = request.files['file1']
    target = os.path.join('./static/', 'file')
    if not os.path.isdir(target):
        os.makedirs(target)
    print(target)
    filename = file.filename
    destination = "/".join([target, filename])
    print(destination)
    file.save(destination)
    print("saved")
    datafile = open(destination, "rb")
    datafile.close()

    b1 = open(destination, 'rb').read()
    target1 = os.path.join('./static/', 'file')
    destination = "/".join([target, filename])
    bucket_resource.upload_file(
        Bucket=bucket_name,
        Filename=destination,
        Key=destination
    )

    response = client.detect_faces(Image={'S3Object':
                                          {'Bucket': bucket_name,
                                           'Name': destination}},
                                   Attributes=['ALL'])
    for faceDetail in response['FaceDetails']:
        print('The detected face is between ' +
              str(faceDetail['AgeRange']['Low']) +
              ' and ' + str(faceDetail['AgeRange']['High']) +
              ' years old')
        output.append(str(faceDetail['AgeRange']['Low']))
        output.append(str(faceDetail['AgeRange']['High']))
        output.append(str(faceDetail['Gender']['Value']))
        output.append(str(faceDetail['Gender']['Confidence']))
        attributes.append(str(faceDetail['Eyeglasses']['Value']))
        attributes.append(str(faceDetail['Sunglasses']['Value']))
        attributes.append(str(faceDetail['Mustache']['Value']))
        attributes.append(str(faceDetail['Beard']['Value']))
        for emotion in faceDetail['Emotions']:
            output.append((emotion['Confidence']))
            output.append((emotion['Type']))
    # extracting json and simpifying it for the webpage
    sung=[]
    eyeg=[]
    musg=[]
    if attributes[0] == 'True':
        if output[2] == 'Female':
            eyeg.append('4. She is wearing glasses.')
        else:
            eyeg.append('4. He is wearing glasses.')
    if attributes[0] == 'True':
        if attributes[1] == 'True':
            if output[2] == 'Female':
                sung.append('5. She is wearing sunglasses.')
            else:
                sung.append('5. He is wearing sunglasses.')
    elif output[2] == 'Female' and attributes[1] == 'True':
        sung.append('4. She is wearing sunglasses.')
    elif output[2] == 'Male' and attributes[1] == 'True':
        sung.append('4. He is wearing sunglasses.')

    if output[2] == 'Male':
        if attributes[0] == 'True' and attributes[1] == 'True':
            if attributes[3] == 'True':
                if attributes[2] == 'True':
                    musg.append('6. He has mustache and beard.')
                else:
                    musg.append('6. He has beard.')
            elif attributes[2] == 'True':
                musg.append('6. He has mustache.')
        elif attributes[0] == 'True' and attributes[1] == 'False':
            if attributes[3] == 'True':
                if attributes[2] == 'True':
                    musg.append('5. He has mustache and beard.')
                else:
                    musg.append('5. He has beard.')
            elif attributes[2] == 'True':
                musg.append('5. He has mustache.')
        elif attributes[0] == 'False' and attributes[1] == 'False':
            if attributes[3] == 'True':
                if attributes[2] == 'True':
                    musg.append('4. He has mustache and beard.')
                else:
                    musg.append('4. He has beard.')
            elif attributes[2] == 'True':
                musg.append('4. He has mustache.')
        elif attributes[0] == 'False' and attributes[1] == 'True':
            if attributes[3] == 'True':
                if attributes[2] == 'True':
                    musg.append('5. He has mustache and beard.')
                else:
                    musg.append('5. He has beard.')
            elif attributes[2] == 'True':
                musg.append('5. He has mustache.')
    firstName = request.form['username']
    conn = mysql.connect()
    cur = conn.cursor()
    print(filename)
    cur.execute("INSERT INTO `faceanalyze`.`analysis`(username, image, "
                "imagename, gender, genderconfidence, agelower, agehigher)"
                " VALUES (%s, %s,%s, %s, %s, %s, %s)",
                (firstName, destination, filename,
                 str(output[2]), str(output[3]), str(output[0]),
                 str(output[1])))
    conn.commit()
    cur.close()
    print('success')
    prepare = ('Analyzing the image:')
    genders = ('1. Gender of the person in image is' + ' ' + output[2] + ' ' +
               'with' + ' ' + output[3] + '% confidence.')
    age = ('2. The person is  between ' + output[0] + ' and '
           + output[1] + ' years old.')
    emotion = ('3. The emotion of person in the image is ' +
               str(output[4]) + ' % ' + str(output[5] + '.'))
    return render_template("index.html", analyzed_text=prepare,
                           address=filename, genders=genders,
                           age=age, emotion=emotion, sun=sung,
                           eye=eyeg, musg=musg)


@app.route('/analyzed', methods=['POST'])
def analyzed():
    """
        Makes the connection to the mysql database
        and get the user information.
        Returns
        ----------
            User(array): All the participants' name
                                 saved in the database.
            Gender(array): Extract the gender column
                                  of the user.
            Agerange(array): Extrats both lower and
                                     higher range of the age
            Imagename(array): Finds the name of avatar saved of users.
        Renders
        ------------
            index.html(page): Returns to the base webpage

    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `faceanalyze`.`analysis`")
    data = cursor.fetchall()
    user = []
    gender = []
    agelower = []
    agehigher = []
    imagename = []
    for row in data:
        user.append(row[1])
        gender.append(row[3])
        agelower.append(row[5])
        agehigher.append(row[6])
        imagename.append(row[7])
        print(imagename)
    return render_template("index.html", user=user,
                           gender=gender, agelower=agelower,
                           agehigher=agehigher, imagename=imagename)


if __name__ == "__main__":
    app.run(debug=True)
