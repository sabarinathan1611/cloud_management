from flask import Blueprint, render_template, request, flash, redirect, url_for,jsonify
from . import db
from .models import User,Text,File
from flask_login import login_required,current_user
from .sysinfo import *
from .functions import dict_to_string,string_to_dict,generate_filename
from .forms import *
from flask  import current_app as app
from .TextEncryption import text_encryption,text_decryption
from .dataencryption import *
from .config import Config
import os
from werkzeug.utils import secure_filename
import threading
import base64
from .fileencryption import *
aes_cipher = AESCipher()

view = Blueprint('view', __name__)


@view.route('/',methods=['POST','GET'])
@login_required
def home():
    fileform=FileForm()
    form = PasswordForm()
    if current_user.is_verified != True:
        
        return redirect(url_for('auth.logout'))

    return render_template('index.html',form=form,fileform=fileform)



    
@view.route('/admin',methods=['POST','GET'])
@login_required
def admin():
    
    if current_user.role == 'admin':
        system_info_printer = SystemInfoPrinter()
        storage_info= system_info_printer.print_storage_info()
        system_info =system_info_printer.print_system_info()

    else: 
        flash("You Don't have a Access")
        return redirect(url_for('view.home'))


    return render_template ('admin.html',storage_info=storage_info,system_info=system_info)

@view.route('/password',methods=['POST'])
@login_required
def store_pass():
    form = PasswordForm()
    if request.method == 'POST' and form.validate_on_submit():
        url = form.url.data
        name=form.name.data
        username=form.username.data
        password=form.password.data
        keypath=app.config['KEY_FOLDER']
        data={'url':url,'name':name,'username':username,'password':password,'keypath':keypath}
        print("DATA: ",type(data))
        string=dict_to_string(data)
        public_key_path=keypath+generate_filename('der')
        print(public_key_path)
        encrypted_public=aes_cipher.encrypt_data(public_key_path)
        private_key_path=keypath+generate_filename('der')
        print(private_key_path)
        encrypted_private=aes_cipher.encrypt_data(private_key_path)

        encrypted_session_key, iv, ciphertext = text_encryption(public_key_path, private_key_path, string)
        stype=aes_cipher.encrypt_data("password")
        newtext =Text(user_id=current_user.id,encrypted_Key=encrypted_session_key,nonce=iv,ciphertext=ciphertext,private_key_path=encrypted_private,public_key_path=encrypted_public,store_type=stype)
        db.session.add(newtext)
        db.session.commit()
    return redirect(url_for('view.home'))

@view.route('/showpass',methods=['POST','GET'])
@login_required
def showpass():
    if current_user.is_authenticated:
        passwords = Text.query.filter_by(user_id=current_user.id)
        data=[]
        for  password in passwords:
            decrypted_message=text_decryption(public_key_path=aes_cipher.decrypt_data(password.public_key_path),private_key_path=aes_cipher.decrypt_data(password.private_key_path),encrypted_session_key=password.encrypted_Key,iv=password.nonce,ciphertext=password.ciphertext)
            data.append({
                "id":password.id,
                "data":string_to_dict(decrypted_message),
                "store_type":aes_cipher.decrypt_data(password.store_type)
                })
        print("DATA:",data,'\n')
        
        return render_template('passwords.html', data=data)
    else:
        return redirect(url_for('view.home'))

@view.route('/uploadfile', methods=['POST'])
@login_required
def fileuplod():
    form = FileForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], generate_filename('file')+filename)
        filemimetype=file.mimetype
        file.save(filepath)
        #print("File:", filepath)
        keypath=app.config['KEY_FOLDER']
        public_key_path=keypath+generate_filename('der')
        private_key_path=keypath+generate_filename('der')
        encryption_instance = File_Encryption()
        key_pair = encryption_instance.generate_key_pair()
        public_key = key_pair.publickey()
        private_key = key_pair
        encryption_instance.save_key_to_file(public_key, public_key_path)
        encryption_instance.save_key_to_file(private_key, private_key_path)
        public_key = encryption_instance.load_key_from_file(public_key_path)
        output=os.path.join(app.config['UPLOAD_FOLDER'], generate_filename('file')+'.bin')
        print("\n\n\n",output,'\n',type(output),'\n\n')
        encryption_instance.encrypt_file(filepath,output, public_key)

        addnew=File(filename=aes_cipher.encrypt_data(filename),filetype=aes_cipher.encrypt_data(file.mimetype),filepath=aes_cipher.encrypt_data(output),private_key_path=aes_cipher.encrypt_data(private_key_path),public_key_path=aes_cipher.encrypt_data(public_key_path),user_id=current_user.id,mimetype=aes_cipher.encrypt_data(file.mimetype))
        db.session.add(addnew)
        db.session.commit()
        thread = threading.Thread(target=os.remove, args=(filepath,))
        thread.start()

    return filename


@view.route('/decrypt')
@login_required
def decrypt_file():
# Get all files associated with the current user
    user_files = current_user.files  # Assuming 'files' is the relationship between User and File models

    # Initialize a list to store image data
    image_data_list = []

    # Decrypt and encode each file's data
    for file in user_files:
        file_path = aes_cipher.decrypt_data(file.filepath)
        private_key_path = aes_cipher.decrypt_data(file.private_key_path)

        # Decrypt the file
        decryption_instance = File_Decryption()
        private_key = decryption_instance.load_key_from_file(private_key_path)
        decrypted_data = decryption_instance.decrypt_file(file_path, private_key)

        # Base64 encode the decrypted image data
        decrypted_data_base64 = base64.b64encode(decrypted_data).decode('utf-8')

        mimetype = aes_cipher.decrypt_data(file.mimetype)

        # Append the image data to the list
        image_data_list.append({
            'decrypted_data_base64': decrypted_data_base64,
            'mimetype': mimetype
        })

    # Pass the list of image data to the template
    return render_template('decrypted_image.html', image_data_list=image_data_list)