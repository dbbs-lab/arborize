import numpy as np, math

def rotate(v0, v):
    """
        Return a builder function that rotates all section arrays (soma, dend, axon).

        Transforming a morphology every time it is loaded is not efficient. Instead use
        this function to rotate the morphology, then save it to a format that can be
        loaded directly. This way the rotation step can be removed.
    """
    # Get the rotation matrix for the transformation of v0 to v.
    R = get_rotation_matrix(v0, v)
    # Create a builder function that changes all the pt3d information of all sections in
    # the soma, dend or axon arrays according to this rotation.
    def builder(model, *args, **kwargs):
        # Loop over the sections
        for s in iter(model.soma + model.dend + model.axon):
            # Loop over the pt3d
            for i in range(s.n3d()):
                # Get the rotated point
                pt0 = np.array([s.x3d(i), s.y3d(i), s.z3d(i)])
                pt = R.dot(pt0)
                # Change the pt3d information
                s.pt3dchange(i, *pt, s.diam3d(i))
    # Return the product function
    return builder


def get_rotation_matrix(v0, v):
    I = np.identity(3)
    # Reduce 1-size dimensions
    v0 = np.array(v0).squeeze()
    v = np.array(v).squeeze()

    # Normalize orientation vectors
    v0 = v0 / np.linalg.norm(v0)
    v = v / np.linalg.norm(v0)
    alpha = np.arccos(np.dot(v0, v))

    if math.isclose(alpha, 0.0):
        report(
            "Rotating morphology between parallel orientation vectors, {} and {}!".format(
                v0, v
            ),
            level=3,
        )
        # We will not rotate the morphology, thus R = I
        return I
    elif math.isclose(alpha, np.pi):
        report(
            "Rotating morphology between antiparallel orientation vectors, {} and {}!".format(
                v0, v
            ),
            level=3,
        )
        # We will rotate the morphology of 180° around a vector orthogonal to the starting
        # vector v0 (the same would be if we take the ending vector v) We set the first
        # and second components to 1; the third one is obtained to have the scalar product
        # with v0 equal to 0
        kx, ky = 1, 1
        kz = -(v0[0] + v0[1]) / v0[2]
        k = np.array([kx, ky, kz])
    else:
        k = (np.cross(v0, v)) / math.sin(alpha)
        k = k / np.linalg.norm(k)

    # Rodrigues' formula
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = (
        I
        + math.sin(alpha) * K
        + (1 - math.cos(alpha)) * np.linalg.matrix_power(K, 2)
    )
    return R
