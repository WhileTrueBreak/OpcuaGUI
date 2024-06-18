from utils.objMesh import ObjMesh
from utils.debug import timing

class WallBuilder:

    S1 = 1
    S2 = 2

    def buildPlaneXY(x, y, z, dx, dy, vis=3):
        vertices_xy = []
        if (vis & WallBuilder.S1)!=0:
            vertices_xy.extend([
                [x,y,z],[x+dx,y,z],[x,y+dy,z],
                [x,y+dy,z],[x+dx,y,z],[x+dx,y+dy,z]])
        if (vis & WallBuilder.S2)!=0:
            vertices_xy.extend([
                [x,y,z],[x,y+dy,z],[x+dx,y,z],
                [x+dx,y,z],[x,y+dy,z],[x+dx,y+dy,z]])
        planexy = ObjMesh.fromVertices(vertices_xy)[0]
        return planexy
   
    def buildPlaneXZ(x, y, z, dx, dz, vis=3):
        vertices_xz = []
        if (vis & WallBuilder.S1)!=0:
            vertices_xz.extend([
                [x,y,z],[x+dx,y,z],[x,y,z+dz],
                [x,y,z+dz],[x+dx,y,z],[x+dx,y,z+dz]])
        if (vis & WallBuilder.S2)!=0:
            vertices_xz.extend([
                [x,y,z],[x,y,z+dz],[x+dx,y,z],
                [x+dx,y,z],[x,y,z+dz],[x+dx,y,z+dz]])
        planexz = ObjMesh.fromVertices(vertices_xz)[0]
        return planexz
    
    def buildPlaneYZ(x, y, z, dy, dz, vis=3):
        vertices_yz = []
        if (vis & WallBuilder.S1)!=0:
            vertices_yz.extend([
                [x,y,z],[x,y+dy,z],[x,y,z+dz],
                [x,y,z+dz],[x,y+dy,z],[x,y+dy,z+dz]])
        if (vis & WallBuilder.S2)!=0:
            vertices_yz.extend([
                [x,y,z],[x,y,z+dz],[x,y+dy,z],
                [x,y+dy,z],[x,y,z+dz],[x,y+dy,z+dz]])
        planeyz = ObjMesh.fromVertices(vertices_yz)[0] 
        return planeyz
    
    def buildPlaneFromPoints(point1, point2, point3, point4, vis=3):
        # Define vertices from the four input points
        # Visibility options for one way planes
        vertices = []
        if (vis & WallBuilder.S1)!=0:
            vertices.extend([
                point1, point2, point3,
                point3, point4, point1])
        if (vis & WallBuilder.S2)!=0:
            vertices.extend([
                point3, point2, point1,
                point1, point4, point3])
        # Create model object from vertices
        plane = ObjMesh.fromVertices(vertices)[0]
        # Add model object to model renderer and return handle to the model
        return plane

    @timing
    def buildWallPlan(wallplan):
        planes = []
        appendPlane = planes.append
        for wall in wallplan:
            point1 = (wall[0][0], wall[0][1], wall[2][0])
            point2 = (wall[1][0], wall[1][1], wall[2][0])
            point3 = (wall[1][0], wall[1][1], wall[2][1])
            point4 = (wall[0][0], wall[0][1], wall[2][1])
            appendPlane(WallBuilder.buildPlaneFromPoints(point1, point2, point3, point4, vis=WallBuilder.S1|WallBuilder.S2))
        return planes

