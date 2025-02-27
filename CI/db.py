import collections
import yaml

import numpy as np

import pandas as pd
import psycopg2


db_config = None

class DB(object):
    def __init__(self):
        global db_config
        if db_config is None:
            db_config = yaml.safe_load(open('db.yaml'))
        self.conn = psycopg2.connect(**db_config)
    def query(self, sql, dates=None):
        return pd.read_sql(sql, self.conn, parse_dates=dates)
    def select(self, table, what, where=None, limit=10, order=None, dates=None):
        sql = f'select {what} from {table}'
        if where is not None:
            sql += f' where {where}'
        if order is not None:
            sql += f' order by {order}'
        if limit is not None:
            sql += f' limit {limit}'
        return self.query(sql, dates)


class NightTelemetry(object):
    """Lookup telemetry using a cache of local noon-noon results.
    """
    def __init__(self, db, tablename, columns='*', cachesize=10, timestamp='time_recorded', verbose=False):
        # Run a test query.
        test = db.select('telemetry.' + tablename, columns, limit=1)
        self.db = db
        self.cachesize = int(cachesize)
        self.tablename = tablename
        self.columns = list(test.columns)
        if timestamp not in self.columns:
            self.columns.append(timestamp)
        self.what = ','.join(self.columns)
        self.timestamp = timestamp
        if verbose:
            print(f'Initialized telemetry from {self.tablename} for {self.what}.')
        self.cache = collections.OrderedDict()
        self.MJD_epoch = pd.Timestamp('1858-11-17', tz='UTC')
        self.one_day = pd.Timedelta('1 days')

    def __call__(self, night, what=None, MJD=None):
        if what is not None and what not in self.columns:
            raise ValueError(f'Invalid column name "{what}". Pick from {self.what}.')
        if night not in self.cache or MJD is not None:
            # Calculate local noon on night.
            when = datetime.datetime.strptime(str(night), '%Y%m%d')
            tmin = when.replace(hour=7)
            # Fetch data until local noon the next day.
            tmax = tmin + datetime.timedelta(days=1)
            # Convert to UTC timestamps.
            tmin = pd.Timestamp(tmin, tz='UTC')
            tmax = pd.Timestamp(tmax, tz='UTC')
        if MJD is not None:
            MJD = np.asarray(MJD)
            # Check that the min MJD is within our range.
            timestamp = self.MJD_epoch + MJD.min() * self.one_day
            if timestamp < tmin or timestamp > tmax:
                raise ValueError(f'MJD {MJD.min()} ({timestamp}) not in night {night}.')
            # Check that the max MJD is within our range.
            timestamp = self.MJD_epoch + MJD.max() * self.one_day
            if timestamp < tmin or timestamp > tmax:
                raise ValueError(f'MJD {MJD.max()} ({timestamp}) not in night {night}.')
        if night not in self.cache:
            # Fetch the results.
            results = self.db.select(
                self.tablename, self.what, limit=None,
                where=f"{self.timestamp}>=TIMESTAMP '{tmin}' and {self.timestamp}<=TIMESTAMP '{tmax}'")
            # Convert the timestamp column to MJD.
            results['MJD'] = (results[self.timestamp] - self.MJD_epoch) / self.one_day
            # Cache the results.
            self.cache[night] = results
            # Trim the cache if necessary.
            while len(self.cache) > self.cachesize:
                self.cache.popitem(last=False)
            assert len(self.cache) <= self.cachesize
        # Fetched the cached results.
        results = self.cache[night]
        if what is None:
            return results
        # Select the specified column (in addition to MJD).
        results = results[['MJD', what]]
        if MJD is None:
            return results
        # Interpolate to the specified time (assuming "what" is numeric).
        dtype = results[what].dtype
        if not np.issubdtype(dtype, np.number):
            raise ValueError(f'Nearest neighbor lookup not implemented yet for dtype "{dtype}".')
        return np.interp(MJD, results['MJD'], results[what])
