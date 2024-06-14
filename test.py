import numpy as np

a = np.array([1,2,3])
b = np.array([4,5,6])

corners = np.array(
    np.meshgrid(
        [a[0], b[0]],
        [a[1], b[1]],
        [a[2], b[2]],
    )
).T.reshape(-1,3)
corners = np.hstack([corners, np.ones((corners.shape[0],1))])
print(corners)