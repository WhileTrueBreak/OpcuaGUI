import time
import os, io, sys

from stl import mesh as stlmesh
import pywavefront
import pickle
# from vedo import Mesh
import numpy as np

from utils.debug import *

class ObjMesh:

    SerialMap = {}

    @classmethod
    def fromSTL(cls, file, transform=np.identity(4)):
        # suppress prints from stlmesh
        text_trap = io.StringIO()
        sys.stdout = text_trap

        mesh = stlmesh.Mesh.from_file(file)

        # restore stdout
        sys.stdout = sys.__stdout__

        numVertices = len(mesh.vectors) * 3
        vertices = np.zeros((numVertices, 8), dtype='float32')
        indices = np.arange(numVertices, dtype='float32')

        normals = np.cross(mesh.vectors[::, 1] - mesh.vectors[::, 0], mesh.vectors[::, 2] - mesh.vectors[::, 0])
        vectors = np.zeros((normals.shape[0], 4))
        vectors[::, 0:3] = normals
        vectors = transform.dot(vectors.T)
        normals = vectors.T[::, 0:3]
        normalMags = np.sqrt((normals ** 2).sum(-1))[..., np.newaxis]
        # divide where x/0 = 0
        normals = np.divide(normals, normalMags, out=np.zeros_like(normals), where=normalMags!=0)
        normals = np.repeat(normals, 3, axis=0)
        vertices[::,3:6] = normals
        
        flattened = mesh.vectors.reshape(mesh.vectors.shape[0]*3, 3)
        vectors = np.ones((flattened.shape[0], 4))
        vectors[::,0:3] = flattened
        vectors = transform.dot(vectors.T)
        vertices[::,0:3] = vectors.T[::,0:3]

        return [cls(vertices, indices)]

    @classmethod
    def fromOBJ(cls, file, transform=np.identity(4)):
        # mesh = Mesh(file)
        # # mesh = mesh.triangulate()
        # mesh.compute_normals()

        # vertices = mesh.vertices
        # verticesT = np.ones((mesh.npoints, 4))
        # verticesT[::,0:3] = vertices
        # verticesT = transform.dot(verticesT.T)
        # vertices = verticesT.T[::,0:3]
        # normals = mesh.vertex_normals
        # normalsT = np.zeros((mesh.npoints, 4))
        # normalsT[::,0:3] = normals
        # normalsT = transform.dot(normalsT.T)
        # normals = normalsT.T[::,0:3]
        # uvs = mesh.pointdata[mesh.pointdata.keys()[0]]
        # if uvs.shape[1] != 2:
        #     uvs = np.zeros((mesh.npoints, 2))
        # vertices = np.hstack((vertices, normals, uvs))
        # indices = np.array(mesh.cells).flatten()

        # return [cls(vertices, indices)]

        scene = pywavefront.Wavefront(file, parse=True)
        models = []
        materials = list(scene.materials.items().mapping.values())
        for material in materials:
            index = [0,1,2,3,3,3,3,3]
            if material.has_uvs and material.has_normals:
                index = [5,6,7,2,3,4,0,1]
            elif material.has_uvs:
                index = [2,3,4,5,5,5,0,1]
            elif material.has_normals:
                index = [3,4,5,0,1,2,6,6]
            vertexSize = material.vertex_size

            vertices = np.array(material.vertices,dtype='float32')
            numVertices = int(len(vertices)/vertexSize)

            indices = np.zeros(numVertices, dtype='float32')
            vertices = vertices.reshape(numVertices, vertexSize)

            zeros = np.zeros((numVertices,1))
            neg = np.tile([-1], (numVertices,1))
            vertices = np.append(vertices, zeros, axis=1)
            vertices = vertices[::,index]
            # generate normal if they dont exist
            if not material.has_normals:
                normals = np.cross(vertices[0::3,0:3] - vertices[1::3,0:3], vertices[0::3,0:3] - vertices[2::3,0:3])
                normals = np.repeat(normals, 3, axis=0)
                vertices[::,3:6] = normals
            # update vertices based on transfromation matrix
            vectors = np.zeros((numVertices, 4))
            vectors[::, 0:3] = vertices[::,3:6]
            vectors = transform.dot(vectors.T)
            vectors = vectors.T[::,0:3]
            vectors /= np.sqrt((vectors ** 2).sum(-1))[..., np.newaxis]
            vertices[::,3:6] = vectors

            vectors = np.ones((numVertices, 4))
            vectors[::, 0:3] = vertices[::,0:3]
            vectors = transform.dot(vectors.T)
            vertices[::,0:3] = vectors.T[::,0:3]
            models.append(cls(vertices, indices))
        return models

    @classmethod
    def fromVertices(cls, vertices, transform=np.identity(4)):
        return [cls(vertices, np.arange(len(vertices)))]
        # vertices = np.array(vertices)
        # unq = np.unique(vertices, axis=0)
        # idx = np.zeros(vertices.shape[0])
        # for i, v in enumerate(vertices):
        #     ridx = np.argwhere(np.all(unq == v, axis = 1))
        #     idx[i] = ridx
        # print(unq, idx)
        # return [cls(unq, idx)]
    
    @classmethod
    def fromVertIndex(cls, vertices, indices, transform=np.identity(4)):
        return [cls(vertices[indices], indices)]

    @classmethod
    def fromSubModels(cls, models):
        vertices = models[0].vertices[models[0].indices]
        for model in models[1:]:
            vertices = np.vstack((vertices, model.vertices[model.indices]))
        return ObjMesh.fromVertices(vertices)

    def __init__(self, vertices, indices):
        self.vertices = np.array(vertices,dtype='float32')
        self.indices = np.array(indices,dtype='int32')
        self.__createVertexData(self.vertices)
        self.__calcBound()
    
    def __createVertexData(self, vertices):
        if len(vertices[0]) == 8: return
        has_uvs = False
        if len(vertices[0]) == 6: return
        if len(vertices[0]) == 5:
            has_uvs = True
            uvs = np.array(vertices[::,3:5])

        vertices = np.array(vertices[::,0:3])
        self.vertices = np.zeros((vertices.shape[0], 8))
        self.vertices[::, 0:3] = vertices

        normals = np.cross(vertices[1::3] - vertices[0::3], vertices[2::3] - vertices[0::3])
        normals /= np.sqrt((normals ** 2).sum(-1))[..., np.newaxis]
        normals = np.repeat(normals, 3, axis=0)
        self.vertices[::,3:6] = normals
        if has_uvs:
            self.vertices[::,6:8] = uvs

    @timing
    def __calcBound(self):
        xyzs = self.vertices[:,0:3]
        minV = np.min(xyzs, axis=0)
        maxV = np.max(xyzs, axis=0)
        self.boundCenter = (minV+maxV)/2
        maxL = np.max(xyzs-self.boundCenter, axis=0)
        self.boundRadius = np.linalg.norm(maxL)
        corners = np.vstack((minV, maxV))

        X, Y, Z = np.meshgrid(corners[:,0], corners[:,1], corners[:,2], indexing='ij')

        # Reshape to combine the coordinates into a single array
        vertices = np.column_stack([X.ravel(), Y.ravel(), Z.ravel(), np.ones((8))])
        self.aabbBound = vertices
    
    @timing
    def generateSubModels(self, maxVerts):
        maxVerts = maxVerts - (maxVerts%3)
        total = self.indices.shape[0]
        models = []
        start = 0
        while start < total:
            asVert = self.vertices[self.indices[start:min(total, start+maxVerts)]]
            models.append(ObjMesh.fromVertices(asVert)[0])
            start += maxVerts
        return models

    def getSphereBound(self, transform=np.identity(4)):
        center_ = np.matmul(transform, np.append(self.boundCenter,1))[0:3]
        radius_ = self.boundRadius*np.max(np.linalg.norm(transform[0:3,0:3],axis=1))
        return center_, radius_
    
    def getAABBBound(self, transform=np.identity(4)):
        vertices_ = np.matmul(self.aabbBound, transform.T)
        return vertices_
    
    @timing
    def serialize(self, loc):
        path = f'{loc}/meshes/{id(self)}'
        if os.path.isfile(path): return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        modelFile = open(path, 'ab')
        pickle.dump({'v':self.vertices, 'i':self.indices}, modelFile)
        modelFile.close()
    
    @classmethod
    @timing
    def deserialize(cls, path, file):
        file = f'{path}/meshes/{file}'
        if file in ObjMesh.SerialMap: return ObjMesh.SerialMap[file]
        meshfile = open(file, 'rb')
        mesh = pickle.load(meshfile)
        model = cls(mesh['v'], mesh['i'])
        meshfile.close()
        ObjMesh.SerialMap[file] = model
        return model



