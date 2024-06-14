#version 430 core

// uniform mat4 transformationMatrix;
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;

uniform samplerCube shadowMap;

layout (std430, binding = 0) buffer transformationMatrices {
  mat4 TMAT[];
};

layout (location = 0) in vec3 vertexPos;
layout (location = 1) in vec3 vertexNormal;
layout (location = 2) in vec4 vertexColor;
layout (location = 3) in float tmatIndex;
layout (location = 4) in vec2 uv;
layout (location = 5) in float texIndex;
layout (location = 6) in float index;

flat out uint objIndex;
flat out int texId;
out vec2 texCoord;
out vec4 worldPos;
out vec4 worldNormal;
flat out vec3 cameraPos;
out vec4 objectColor;
out vec4 lightColor;

// out float shade;
// out vec4 color;

float map(float value, float min1, float max1, float min2, float max2) {
  return min2 + (value - min1) * (max2 - min2) / (max1 - min1);
}

void main() {
  int matIndex = int(tmatIndex);

  objIndex = uint(index);
  texId = int(texIndex);
  texCoord = uv;

  mat4 invVeiwMat = inverse(viewMatrix);
  cameraPos = vec3(invVeiwMat[3][0], invVeiwMat[3][1], invVeiwMat[3][2]);

  worldPos = TMAT[matIndex] * vec4(vertexPos, 1.0);
  worldNormal = TMAT[matIndex] * vec4(vertexNormal, 0.0);

  vec4 relPos = viewMatrix * worldPos;
  vec4 screenPos = projectionMatrix*relPos;

  objectColor = vertexColor;
  lightColor = vec4(1, 1, 1, 1);
  gl_Position = screenPos;
}