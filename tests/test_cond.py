import jax
import jax.numpy as jnp
import pytest

import quax
from quax.examples.unitful import kilograms, meters, Unitful


def _outer_fn(a: jax.Array, b: jax.Array, c: jax.Array, pred: bool | jax.Array):
    def _true_fn(a: jax.Array):
        return a + b

    def _false_fn(a: jax.Array):
        return a + c

    res = jax.lax.cond(pred, _true_fn, _false_fn, a)
    return res


def test_cond_basic():
    a = Unitful(jnp.asarray(1.0), {meters: 1})
    b = Unitful(jnp.asarray(2.0), {meters: 1})
    c = Unitful(jnp.asarray(10.0), {meters: 1})

    res = quax.quaxify(_outer_fn)(a, b, c, False)
    assert res.array == 11
    assert res.units == {meters: 1}

    res = quax.quaxify(_outer_fn)(a, b, c, True)
    assert res.array == 3
    assert res.units == {meters: 1}


def test_cond_different_units():
    a = Unitful(jnp.asarray([1.0]), {meters: 1})
    b = Unitful(jnp.asarray([2.0]), {meters: 1})
    c = Unitful(jnp.asarray([10.0]), {kilograms: 1})

    with pytest.raises(Exception):
        quax.quaxify(_outer_fn)(a, b, c, False)


def test_cond_jit():
    a = Unitful(jnp.asarray(1.0), {meters: 1})
    b = Unitful(jnp.asarray(2.0), {meters: 1})
    c = Unitful(jnp.asarray(10.0), {meters: 1})

    res = quax.quaxify(jax.jit(_outer_fn))(a, b, c, False)
    assert res.array == 11
    assert res.units == {meters: 1}

    res = quax.quaxify(jax.jit(_outer_fn))(a, b, c, True)
    assert res.array == 3
    assert res.units == {meters: 1}


def test_cond_vmap():
    a = Unitful(jnp.arange(1), {meters: 1})
    b = Unitful(jnp.asarray(2), {meters: 1})
    c = Unitful(jnp.arange(2, 13, 2), {meters: 1})
    vmap_fn = jax.vmap(_outer_fn, in_axes=(None, None, 0, None))

    res = quax.quaxify(vmap_fn)(a, b, c, True)
    assert (res.array == a.array + b.array).all()
    assert res.units == {meters: 1}

    res = quax.quaxify(vmap_fn)(a, b, c, False)
    assert (res.array.ravel() == a.array.ravel() + c.array.ravel()).all()  # type: ignore
    assert res.units == {meters: 1}


def test_cond_grad_closure():
    x = Unitful(jnp.asarray(2.0), {meters: 1})
    b = Unitful(jnp.asarray(2.0), {meters: 1})
    c = Unitful(jnp.asarray(10.0), {meters: 1})
    dummy = Unitful(jnp.asarray(1.0), {meters: 1})

    def outer_fn(
        outer_var: jax.Array,
        dummy: jax.Array,
        b: jax.Array,
        c: jax.Array,
        pred: bool | jax.Array,
    ):
        def _true_fn_grad(outer_var: jax.Array):
            return outer_var + b

        def _false_fn_grad(outer_var: jax.Array):
            return outer_var + c

        def _outer_fn_grad(a: jax.Array):
            return jax.lax.cond(pred, _true_fn_grad, _false_fn_grad, a)

        primals = (outer_var,)
        tangents = (dummy,)
        p_out, t_out = jax.jvp(_outer_fn_grad, primals, tangents)
        return p_out, t_out

    p, t = quax.quaxify(outer_fn)(x, dummy, b, c, True)
    assert p.array == 4
    assert p.units == {meters: 1}
    assert t.array == 1
    assert t.units == {meters: 1}

    p, t = quax.quaxify(outer_fn)(x, dummy, b, c, False)
    assert p.array == 12
    assert p.units == {meters: 1}
    assert t.array == 1
    assert t.units == {meters: 1}
