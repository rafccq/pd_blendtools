from math import pi

from mathutils import Euler, Vector, Matrix


def rotM(e):
    return Euler(e).to_matrix().to_4x4()

def rot(a, axis):
    e = (a, 0, 0)
    if axis == 'y':
        e = (0, a, 0)
    elif axis == 'z':
        e = (0, 0, a)

    return rotM(e)

# all doors have a rotation of 90d on the x and z axes
# this function returns an inverse of this rotation
def rot_doorinv():
    Rx = rot(-pi/2,  'x')
    Rz = rot(-pi/2,  'z')
    return Rx @ Rz

def mtx_basis(M):
    vec = lambda mat, i: Vector([mat[k][i] for k in range(3)])

    _loc, rotmat, _sca = M.decompose()
    R = rotmat.to_matrix()
    return vec(R, 0), vec(R, 1), vec(R, 2)

# returns a mtx that properly aligns PD objects in the Blender viewport
# (90d on X and Z axes)
def rot_blender():
    return Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
