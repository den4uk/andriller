import pytest
import tempfile
from andriller import cracking


def test_crack_pattern():
    assert cracking.crack_pattern('C8C0B24A15DC8BBFD411427973574695230458F0') == [0, 3, 6, 7, 8]
    assert cracking.crack_pattern('C8C0B24A15DC8BBFD411427973574695230458F1') == False
    assert cracking.crack_pattern('da39a3ee5e6b4b0d3255bfef95601890afd80709') == None


def test_crack_pin_good():
    _hash = '6EC7A5E2A6309BBEC78763D109219CC8A93F54A820A29E211BAD324DFC8EFC663F42111C'
    _salt = 2044335772077330329
    crack = cracking.PasswordCrack(
        _hash,
        _salt,
        end=999999,
    )
    assert crack.crack_password() == '075369'


def test_crack_as_pw_good():
    _hash = '6EC7A5E2A6309BBEC78763D109219CC8A93F54A820A29E211BAD324DFC8EFC663F42111C'
    _salt = 2044335772077330329
    crack = cracking.PasswordCrack(
        _hash,
        _salt,
        alpha=True,
        alpha_range='a976530',
        min_len=5,
        max_len=6,
    )
    assert crack.crack_password() == '075369'


def test_crack_as_pw_bad():
    with pytest.raises(cracking.PasswordCrackError):
        _hash = '6EC7A5E2A6309BBEC78763D109219CC8A93F54A820A29E211BAD324DFC8EFC663F42111C'
        _salt = 2044335772077330329
        crack = cracking.PasswordCrack(
            _hash,
            _salt,
            alpha=True,
            alpha_range='',
            min_len=5,
            max_len=6,
        )
        crack.crack_password()


def test_crack_as_dict_good():
    with tempfile.NamedTemporaryFile() as tf:
        with open(tf.name, 'wb') as f:
            f.write(b'abc\n075369\nboom\n')
        _hash = '6EC7A5E2A6309BBEC78763D109219CC8A93F54A820A29E211BAD324DFC8EFC663F42111C'
        _salt = 2044335772077330329
        crack = cracking.PasswordCrack(
            _hash,
            _salt,
            alpha=True,
            dict_file=tf.name,
        )
        assert crack.crack_password() == '075369'


def test_crack_pin_bad():
    _hash = '6EC7A5E2A6309BBEC78763D109219CC8A93F54A820A29E211BAD324DFC8EFC663F421111'
    _salt = 2044335772077330329
    crack = cracking.PasswordCrack(
        _hash,
        _salt,
        start=0,
        end=100,
    )
    assert crack.crack_password() == None


def test_crack_pin_good_sam():
    _hash = 'AA43A64F0859B24255D56DB44BB6B9F6E49188EB'
    _salt = -2037791700271835148
    crack = cracking.PasswordCrack(
        _hash,
        _salt,
        start=0,
        end=1300,
        samsung=True
    )
    assert crack.crack_password() == '1234'


@pytest.mark.parametrize(
    '_hash, _salt',
    [
        (None, None),
        (0, ''),
        ('', 0),
        ('AA43A64F0859B24255D56DB44BB6B9F6E49188EB', ''),
        ('AA43A64F0859B24255D56DB44BB6B9F6E49188EB', '123'),
        ('AA43A64F0859B24255D56DB44BB6B9F6E49188EB', 'not-int'),
        ('not-hash', 'not-int'),
        ('AA43A64F0859B24255D56DB44BB6B9F6E49188EBB', 123),  # too long hash
        ('AA43A64F0859B24255D56DB44BB6B9F6E49188E', 123),  # too short hash
    ]
)
def test_bad_values(_hash, _salt):
    with pytest.raises(cracking.PasswordCrackError):
        cracking.PasswordCrack(_hash, _salt)
