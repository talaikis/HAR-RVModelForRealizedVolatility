import MySQLdb as mdb
import time
import matplotlib.pyplot as plt
import pandas as pd
from pandas.stats.api import ols
from pandas.tools.plotting import autocorrelation_plot
from numpy import sqrt, log, power

scriptStart = time.time()

#connect to DB
def connect_to_DB():
    
    #Connect to the <a href="http://www.talaikis.com/mysql/">MySQL</a> instance
    db_host = '127.0.0.1'
    db_user = 'root'
    db_pass = '8h^=GP655@740u9'
    db_name = 'lean'

    con = mdb.connect(host = db_host, user = db_user, passwd = db_pass, db = db_name)
    
    return con

#disconnect from databse
def disconnect(con):
    # disconnect from server
    con.close()
    
#get data from <a href="http://www.talaikis.com/mysql/">MySQL</a>
def req_sql(sym, con):
    # Select all of the historic close data
    sql = """SELECT * FROM `"""+sym+"""` ORDER BY DATE_TIME ASC;"""
     #create a pandas dataframe
    df = pd.read_sql_query(sql, con=con, index_col='DATE_TIME')

    return df

#Garman Klass volaility estimator function
def Garman_Klass_Volatility_Estimator(df, period):
    oc = log(df['OPEN']) - log(df['CLOSE'].shift())
    co = log(df['CLOSE']) - log(df['OPEN'])
    diff = oc.shift() + co.shift()
    tmp = power(((oc + co) - pd.rolling_mean(diff, window=period)), 2.0)
    hkve = pd.rolling_sum(tmp, window=period) / (period-1.0)
              
    return hkve

#script body
if __name__ == "__main__":
    
    con = connect_to_DB()
    
    sym = ["YAHOO_INDEX_GSPC"]
    wins = []
    xAx = []
    in_sample = True
    
    #get data
    dfHK = req_sql(sym[0], con)
    
    for period in range(0, int(len(dfHK)/21)):
    
        id = pd.DataFrame(index=dfHK.index)
        
        try:
            #get estimators ofro in sample
            id['day'] = Garman_Klass_Volatility_Estimator(dfHK, 2)[21*period:21*(period+3)].dropna()
            id['future'] = Garman_Klass_Volatility_Estimator(dfHK, 2)[21*period:21*(period+3)].shift(-1) #shifted to the future
            id['week'] = Garman_Klass_Volatility_Estimator(dfHK, 5)[21*period:21*(period+3)].dropna()
            id['month'] = Garman_Klass_Volatility_Estimator(dfHK, 21)[21*period:21*(period+3)].dropna()
        
            #get out sample data
            dfHK['day_out'] = Garman_Klass_Volatility_Estimator(dfHK, 2)[(21*period+3):21*(period+6)]
            dfHK['future_out'] = Garman_Klass_Volatility_Estimator(dfHK, 2)[(21*period+3):21*(period+6)].shift(-1) #shifted to the future
            dfHK['week_out'] = Garman_Klass_Volatility_Estimator(dfHK, 5)[(21*period+2):31*(period+6)]
            dfHK['month_out'] = Garman_Klass_Volatility_Estimator(dfHK, 21)[(21*period+3):21*(period+6)]
        
            #make dataset
            data_set_in = pd.concat([id['future'], id['day'], id['week'], id['month']], axis=1, join_axes=[id.index]).dropna()
            data_set_out = pd.concat([dfHK['future_out'], dfHK['day_out'], dfHK['week_out'], dfHK['month_out']], axis=1, join_axes=[dfHK.index]).dropna()
        
            #fit regression
            res_in = ols(y=data_set_in['future'], x=data_set_in[['day','week', 'month']])
            res_out = ols(y=data_set_out['future_out'], x=data_set_out[['day_out','week_out', 'month_out']])
        
            #get results
            #print res
        
            #full formula for out of sample
            HAR =  res_in.beta[0]*data_set_out['day_out'] + res_in.beta[1]*data_set_out['week_out'] + res_in.beta[2]*data_set_out['month_out'] + res_in.beta[3]
    
            #calculate win rates
            l = 0
            w = 0
    
            #get win rates
            if in_sample:
                v = data_set_in['future'].pct_change().dropna()
                f = res_in.y_fitted.pct_change().dropna()
            else:
                v = data_set_out['future_out'].pct_change().dropna()
                f = HAR.pct_change().dropna()
    
            c = pd.concat([v, f], axis=1, join_axes=[v.index]).dropna()
            c.columns = ['O', "T"]
    
            for k in range(0, len(c)):
                if float(c['O'][k]) > 0.0 and float(c['T'][k]) > 0.0:
                    w += 1
                    k += 1
                elif float(c['O'][k]) < 0.0 and float(c['T'][k]) < 0.0:
                    w += 1
                    k += 1
                else:
                    l += 1
                    k += 1  
    
            print "Win rate:"
            print float(w)/float(k)
        
            #make win plot
            wins.append(float(w)/float(k))
            xAx.append(period)
        
            print "Done for period %s" %period
            print "----------------------------------------------"
        except:
            print "Some problem"
            continue
    
    disconnect(con)
    timeused = (time.time()-scriptStart)/60
    print("Done in ",timeused, " minutes")
    
    plt.plot(xAx, wins)
    plt.axhline(0.5, color = 'r', xmax=5)
    avg = sum(wins) / float(len(wins))
    plt.axhline(avg, color = 'r', xmax=5)
    plt.ylabel("Win rate")
    plt.xlabel("Period")
    plt.show()   
    
    #sample <a href="http://www.talaikis.com/autocorrelation/">autocorrelation</a>
    autocorrelation_plot(HAR.pct_change().dropna())
    plt.show()