import pandas
import pymongo
# from flask import jsonify, json
# from bson import json_util
import json
import os
from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import permission_classes
from rest_framework import permissions
from import_data.serializers import ImportDataSerializer
from rest_framework import status


@permission_classes((permissions.AllowAny,))
class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    # authentication_classes = (JSONWebTokenAuthentication, )

    def post(self, request, format=None):
        file_obj = request.data['file']
        project_id = request.data['project']
        serializer = ImportDataSerializer(data=request.data)
        if serializer.is_valid():
            file_path = '/code/tmp/' + file_obj.name
            if not file_obj.name.endswith('.csv'):
                return Response(status=status.HTTP_400_BAD_REQUEST)

            else:
                with default_storage.open(file_path, 'wb+') as dest:
                    for chunk in file_obj.chunks():
                        dest.write(chunk)

                dataframe = pandas.read_csv(file_path)
                json_data = json.loads(dataframe.to_json(orient="records"))

                mongo_client = pymongo.MongoClient('mongo', 27017)
                mongo_db = mongo_client['main_db']
                collection = mongo_db['collection_' + project_id]
                collection.insert(json_data)
                serializer.save()
                os.remove(file_path)

                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@permission_classes((permissions.AllowAny,))
class FileUploadViewDetail(APIView):

    def get(self, request, pk, format=None):
        mongo_client = pymongo.MongoClient('mongo', 27017)
        mongo_db = mongo_client['main_db']
        collection = mongo_db['collection_' + str(pk)]
        if collection.count() == 0:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            elements = collection.find({})
            json_docs = []
            for doc in elements:
                print(type(doc))
                # json_doc = json.dumps(doc, default=json_util.default)
                json_doc = str(doc)
                json_docs.append(json_doc)
                json_data = json.dumps(json_docs, ensure_ascii=False)
            return Response(json_data, status=status.HTTP_200_OK)

    def put(self, request, pk, format=None):
        remove_field = request.data['remove_field']
        mongo_client = pymongo.MongoClient('mongo', 27017)
        mongo_db = mongo_client['main_db']
        collection = mongo_db['collection_' + str(pk)]
        if collection.count() == 0:
            return Response(status=status.HTTP_404_NOT_FOUND)
        else:
            collection.update({}, {'$unset': {remove_field: 1}}, multi=True)
