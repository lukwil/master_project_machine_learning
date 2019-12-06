import pandas as pd
import ast
from datetime import datetime, timedelta
from pymongo import MongoClient
import mongodb_connection
import matplotlib.pyplot as plt
import copy

def importMessprotokoll(path):
    df = pd.read_csv(path, sep=';')
    df.rename(columns=lambda x: x.strip(), inplace=True)
    df["Measured"] = df["Measured"].apply(lambda x: float(str(x).replace(',','.')))
    df["Setpoint"] = df["Setpoint"].apply(lambda x: float(str(x).replace(',','.')))
    df["Difference"] = df["Difference"].apply(lambda x: float(str(x).replace(',','.')))
    columnsToStrip = ["Program", "Plane", "Measuring variant","Results:", "Unit"]
    for curColumn in columnsToStrip:
        df[curColumn] = df[curColumn].apply(lambda x: x.strip())
    return df

def importAchsleistungCSV(path):
    return pd.read_csv(path, sep=';')

def importMessDatasetCSV(path):
    return pd.read_csv(path, sep=',', header=6)

# für Tabelle values und values_actual
def importJSONExport(path):
    df = pd.read_json(path,orient="records", lines=True)
    df["_id"] = df["_id"].apply(lambda x: x["$oid"])
    df["timeStamp"] = df["timeStamp"].apply(lambda x: x["$date"]).apply(lambda x: x["$numberLong"]).apply(int)
    df["valueStatus"] = df["valueStatus"].apply(lambda x: x["$numberInt"])
    if "value_number" in df.columns:
        df["value_number"] = df["value_number"].apply(lambda x: list(x.values())[0])
    df["timeStampMqttClient"] = df["timeStampMqttClient"].apply(lambda x: x["$date"]).apply(lambda x: x["$numberLong"])
    return df

# für Tabelle values_ncprogram
def importJSONExportNCProg(path):
    return 0

def joinByBinnedTimestampXY(dataframe, timeStampBin=2):
    dfX = dataframe.loc[lambda x: x["ValueID"]=="12430012063.X1_Axis.Actual_Position_MCS", ["ValueID","value","timeStamp"]].sort_values(by=["timeStamp"])
    dfY = dataframe.loc[lambda x: x["ValueID"]=="12430012063.Y1_Axis.Actual_Position_MCS", ["ValueID", "value","timeStamp"]].sort_values(by=["timeStamp"])
    #bin
    dfX['timeStamp'] = dfX['timeStamp'].apply(lambda x: int(x)-(int(x)%(10**timeStampBin)))
    dfY['timeStamp'] = dfY['timeStamp'].apply(lambda x: int(x)-(int(x)%(10**timeStampBin)))
    #group
    dfX = dfX.groupby(by="timeStamp").mean()
    dfX.rename(columns={"value":"X"}, inplace = True)
    dfY = dfY.groupby(by="timeStamp").mean()
    dfY.rename(columns={"value":"Y"}, inplace=True)
    #join
    joined = dfX.join(dfY, how='inner')
    joined.reset_index(inplace = True)
    return joined

def loadReibdatenFromMongoDB(tsStart,tsEnd):
    client = MongoClient(mongodb_connection.connectionstring)
    db = client.DMG_CELOS_MOBILE_V3_CA
    collection = db["values_ncprogram"]
    cursor = collection.find({
        'timeStamp' : {'$gt':tsStart, '$lt':tsEnd},
        'toolNo' : 'RA_12H7' # $gt: greater than, $lt: less than
    }).batch_size(10000)
    df = pd.DataFrame(columns=['_id','ValueID','value','timeStamp','progName','toolNo'])
    i = 0
    for item in cursor:
        df.loc[i] = [item['_id'],item['ValueID'],item['value_number'],item['timeStamp'], item['progName'],item['toolNo']]
        if i%10000 == 0:
            print(i,end=', ')
        i=i+1
        
    return df

def loadxAxisDataFromMongoDB(tsStart = datetime(2019,11,26,12,15), tsEnd = datetime(2019,11,26,13,10)):
    client = MongoClient(mongodb_connection.connectionstring)
    db = client.DMG_CELOS_MOBILE_V3_CA
    collection = db["values"]
    # for a first, get documents between 26.11.2019, 9:30 and 26.11.2019, 23:59
    # only get documents with ValueID = 12430012063.X1_Axis.Actual_Position_MCS
    vID = "12430012063.X1_Axis.Actual_Position_MCS"
    
    cursor = collection.find({
            'timeStamp' : {'$gt':tsStart, '$lt':tsEnd} # $gt: greater than, $lt: less than
            })
    df = pd.DataFrame(columns=['_id','ValueID','value','timeStamp'])
    i = 0
    for item in cursor:
        df.loc[i] = [item['_id'],item['ValueID'],item['value_number'],item['timeStamp']]
        i+=1
        
    return df

def plotSpecificIDs(idList, df):
    tsStart = datetime(2019,11,26,12,0)
    tsEnd = datetime(2019,11,26,23,35)
    plt.figure(figsize=(15, 5), dpi=80)
    plt.plot(df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp'])& (l['timeStamp'] < tsEnd), "timeStamp"],df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp']) & (l['timeStamp'] < tsEnd), 'value'], c='r')
    for id in idList:
        plt.scatter(df.loc[lambda l: (l['ValueID']==id) & (tsStart < l['timeStamp'])& (l['timeStamp'] < tsEnd), "timeStamp"],df.loc[lambda l: (l['ValueID']==id) & (tsStart < l['timeStamp'])& (l['timeStamp'] < tsEnd), "value"], s=1)
    plt.legend(["12430012063.Z1_Axis.Actual_Position_MCS"]+idList)
    plt.show()
    
def plotActualZ1(df, tsStart = datetime(2019,11,26,12,0), tsEnd = datetime(2019,11,26,23,35)):
    plt.figure(figsize=(15, 5), dpi=80)
    plt.plot(df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp'])& (l['timeStamp'] < tsEnd), "timeStamp"],df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp']) & (l['timeStamp'] < tsEnd), 'value'], c='r')
    plt.scatter(df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp'])& (l['timeStamp'] < tsEnd), "timeStamp"],df.loc[lambda l: (l['ValueID']=="12430012063.Z1_Axis.Actual_Position_MCS") & (tsStart < l['timeStamp']) & (l['timeStamp'] < tsEnd), 'value'], c='b',s=1.0)
    plt.legend(["12430012063.Z1_Axis.Actual_Position_MCS","12430012063.Z1_Axis.Actual_Position_MCS"])
    plt.show()

def approxRange(dfParent,start,end,minValue,maxValue,deltaTime):
    valueID_Z1 = "12430012063.Z1_Axis.Actual_Position_MCS"
    newStart = copy.deepcopy(start)
    newEnd = copy.deepcopy(end)
    tempDF = dfParent.loc[lambda d: (d["ValueID"] == valueID_Z1) & (start < d["timeStamp"]) & (d["timeStamp"] < end)]
    
    #approx. start of frame
    runAtLeastOnce = False
    while minValue < tempDF.loc[:,"value"].min() and tempDF.loc[:,"value"].max() < maxValue:
        newStart = newStart - deltaTime
        tempDF = dfParent.loc[lambda l: (l["ValueID"] == valueID_Z1) & (newStart < l["timeStamp"]) & (l["timeStamp"] < newEnd)]
        runAtLeastOnce = True
    
    if runAtLeastOnce:
        newStart = newStart + deltaTime
    tempDF = dfParent.loc[lambda l: (l["ValueID"] == valueID_Z1) & (newStart < l["timeStamp"]) & (l["timeStamp"] < newEnd)]
    
    #approx. end of frame
    runAtLeastOnce = False
    while minValue < tempDF.loc[:,"value"].min() and tempDF.loc[:,"value"].max() < maxValue:
        newEnd = newEnd + deltaTime
        tempDF = dfParent.loc[lambda l: (l["ValueID"] == valueID_Z1) & (newStart < l["timeStamp"]) & (l["timeStamp"] < newEnd)]
        runAtLeastOnce = True
    
    if runAtLeastOnce:
        newEnd = newEnd - deltaTime
    
    return newStart, newEnd

def approxRangeInSteps(dfParent,initialStart,initialEnd,deltaTimes=[timedelta(minutes=5),timedelta(seconds=30),timedelta(seconds=5),timedelta(seconds=1)],sampleTolerance=5):
    valueID_Z1 = "12430012063.Z1_Axis.Actual_Position_MCS"
    start = initialStart
    end = initialEnd
    tempDF = dfParent.loc[lambda d: (d["ValueID"] == valueID_Z1) & (start < d["timeStamp"]) & (d["timeStamp"] < end)]
    minValue = tempDF.loc[:,"value"].min() - sampleTolerance
    maxValue = tempDF.loc[:,"value"].max() + sampleTolerance
    print(minValue)
    print(maxValue)
    for dT in deltaTimes:
        start, end = approxRange(dfParent,start,end,minValue,maxValue,dT)
    return start,end   