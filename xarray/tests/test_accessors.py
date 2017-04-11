from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
try:
    import cPickle as pickle
except ImportError:
    import pickle

import xarray as xr
import numpy as np
import pandas as pd

from . import TestCase, requires_dask


class TestDatetimeAccessor(TestCase):
    def setUp(self):
        nt = 100
        data = np.random.rand(10, 10, nt)
        lons = np.linspace(0, 11, 10)
        lats = np.linspace(0, 20, 10)
        self.times = pd.date_range(start="2000/01/01", freq='H', periods=nt)
        self.times_arr = np.random.choice(self.times, size=(10, 10, nt))

        self.data = xr.DataArray(data, coords=[lons, lats, self.times],
                                 dims=['lon', 'lat', 'time'], name='data')

    def test_field_access(self):
        years = xr.DataArray(self.times.year, name='year',
                             coords=[self.times, ], dims=['time', ])
        months = xr.DataArray(self.times.month, name='month',
                             coords=[self.times, ], dims=['time', ])
        days = xr.DataArray(self.times.day, name='day',
                             coords=[self.times, ], dims=['time', ])
        hours = xr.DataArray(self.times.hour, name='hour',
                             coords=[self.times, ], dims=['time', ])


        self.assertDataArrayEqual(years, self.data.time.dt.year)
        self.assertDataArrayEqual(months, self.data.time.dt.month)
        self.assertDataArrayEqual(days, self.data.time.dt.day)
        self.assertDataArrayEqual(hours, self.data.time.dt.hour)

    def test_not_datetime_type(self):
        nontime_data = self.data.copy()
        int_data = np.arange(len(self.data.time)).astype('int8')
        nontime_data['time'].values = int_data
        with self.assertRaisesRegexp(TypeError, 'dt'):
            nontime_data.time.dt.year

    @requires_dask
    def test_dask_field_access(self):
        import dask.array as da

        # Safely pre-compute comparison fields by passing through Pandas
        # machinery
        def _getattr_and_reshape(arr, attr):
            data = getattr(arr.dt, attr).values.reshape(self.times_arr.shape)
            return xr.DataArray(data, coords=self.data.coords,
                                dims=self.data.dims, name=attr)
        times_arr_as_series = pd.Series(self.times_arr.ravel())
        years = _getattr_and_reshape(times_arr_as_series, 'year')
        months = _getattr_and_reshape(times_arr_as_series,'month')
        days = _getattr_and_reshape(times_arr_as_series, 'day')
        hours = _getattr_and_reshape(times_arr_as_series, 'hour')

        dask_times_arr = da.from_array(self.times_arr, chunks=(5, 5, 50))
        dask_times_2d = xr.DataArray(dask_times_arr,
                                     coords=self.data.coords,
                                     dims=self.data.dims,
                                     name='data')
        dask_year = dask_times_2d.dt.year
        dask_month = dask_times_2d.dt.month
        dask_day = dask_times_2d.dt.day
        dask_hour = dask_times_2d.dt.hour

        # Test that the data isn't eagerly evaluated
        assert isinstance(dask_year.data, da.Array)
        assert isinstance(dask_month.data, da.Array)
        assert isinstance(dask_day.data, da.Array)
        assert isinstance(dask_hour.data, da.Array)

        # Double check that outcome chunksize is unchanged
        dask_chunks = dask_times_2d.chunks
        self.assertEqual(dask_year.data.chunks, dask_chunks)
        self.assertEqual(dask_month.data.chunks, dask_chunks)
        self.assertEqual(dask_day.data.chunks, dask_chunks)
        self.assertEqual(dask_hour.data.chunks, dask_chunks)

        # Check the actual output from the accessors
        self.assertDataArrayEqual(years, dask_year.compute())
        self.assertDataArrayEqual(months, dask_month.compute())
        self.assertDataArrayEqual(days, dask_day.compute())
        self.assertDataArrayEqual(hours, dask_hour.compute())

