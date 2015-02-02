import os
from io import BytesIO

import numpy as np

from amodem import send
from amodem import recv
from amodem import common
from amodem import dsp
from amodem import sampling
from amodem import config
from amodem import async
config = config.fastest()

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')

import pytest


class Args(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return None


def run(size, chan=None, df=0, success=True, reader=None):
    tx_data = os.urandom(size)
    tx_audio = BytesIO()
    send.main(config=config, src=BytesIO(tx_data), dst=tx_audio)

    data = tx_audio.getvalue()
    data = common.loads(data)
    if chan is not None:
        data = chan(data)
    if df:
        sampler = sampling.Sampler(data, sampling.Interpolator())
        sampler.freq += df
        data = sampler.take(len(data))

    data = common.dumps(data)
    rx_audio = BytesIO(data)
    rx_data = BytesIO()
    dump = BytesIO()

    if reader:
        rx_audio = reader(rx_audio)
    try:
        result = recv.main(config=config, src=rx_audio, dst=rx_data,
                           dump_audio=dump)
    finally:
        rx_audio.close()

    rx_data = rx_data.getvalue()
    assert data.startswith(dump.getvalue())

    assert result == success
    if success:
        assert rx_data == tx_data


@pytest.fixture(params=[0, 1, 3, 10, 42, 123])
def small_size(request):
    return request.param


def test_small(small_size):
    run(small_size, chan=lambda x: x)


def test_async():
    run(1024, chan=lambda x: x,
        reader=lambda s: async.AsyncReader(s, 128))


def test_error():
    skip = 32000  # remove trailing silence
    run(1024, chan=lambda x: x[:-skip], success=False)


@pytest.fixture(params=[sign * mag for sign in (+1, -1)
                        for mag in (0.1, 1, 10, 100, 1e3, 2e3)])
def freq_err(request):
    return request.param * 1e-6


def test_timing(freq_err):
    run(8192, df=freq_err)


def test_lowpass():
    run(1024, chan=lambda x: dsp.lfilter(b=[0.9], a=[1.0, -0.1], x=x))


def test_highpass():
    run(1024, chan=lambda x: dsp.lfilter(b=[0.9], a=[1.0, 0.1], x=x))


def test_attenuation():
    run(5120, chan=lambda x: x * 0.1)


def test_low_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.0001))


def test_medium_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.001))


def test_large():
    run(54321, chan=lambda x: x)
