FROM public.ecr.aws/lambda/python:3.9

COPY df_style.css ./
COPY peak_raid_2023.json ./
COPY requirements.txt ./
COPY results.py ./

RUN pip install -r requirements.txt

CMD ["results.lambda_handler"]