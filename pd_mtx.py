from math import pi, radians

from mathutils import Euler, Vector, Matrix


M_BADPI = 3.141092641

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
    C = Matrix([
        [1, 0, 0, 0],
        [0, 0, 1, 0],
        [0, -1, 0, 0],
        [0, 0, 0, 1]
    ])
    rx = Matrix.Rotation(pi/2, 4, 'X')
    ry = Matrix.Rotation(0, 4, 'Y')
    rz = Matrix.Rotation(-pi/2, 4, 'Z')
    rot_lh = rz @ ry @ rx  # ZYX order
    rot_rh = C @ rot_lh @ C.inverted()
    return rot_rh.inverted()

def mtx_basis(M):
    conv = lambda v: Vector((v[0], v[2], -v[1]))
    vec = lambda mat, i: conv([mat[k][i] for k in range(3)])

    _loc, rotmat, _sca = M.decompose()
    R = rotmat.to_matrix()
    return vec(R, 0), vec(R, 1), vec(R, 2)

# returns a mtx that properly aligns PD objects in the Blender viewport
# (90d on X and Z axes)
def rot_blender():
    return rotM((pi/2, 0, pi/2))

def rot_blender_inv():
    return Matrix.Rotation(radians(-90), 4, 'X')

def rot_FLAG00000002inv():
    Rx = rot(-pi * 1.5,  'x')
    Ry = rot(-M_BADPI,  'y')
    return Rx @ Ry

def rot_FLAGUPSIDEDONWinv():
    Rz = rot(-M_BADPI,  'z')
    return Rz
