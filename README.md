Creates weekly summary pages and downloads of required preparation from MedTech

## Install instructions

Setup python and dependencies: 

    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt

    # If using Python < 2.7.9: 
    pip install --upgrade pyOpenSSL ndg-httpsclient pyasn1 requests[security] 

Configure access to MedTech. To do this, create the following files with your
medtech password and calendar url: 

    echo "your password" > .mtpass
    echo "ical URL" > .mturl
