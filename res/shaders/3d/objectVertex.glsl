#version 430 core

// uniform mat4 transformationMatrix;
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;

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
flat out vec3 lightPos;
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

  lightPos = vec3(7, 4, 2);

  // vec3 lightVec1 = normalize(vec3(-0.5, -2, 1));
  // vec3 lightVec2 = normalize(vec3(0.5, 2, -0.5));

  // float shade1 = dot(lightVec1, normalize(tnormal.xyz))/2+0.5;
  // float shade2 = dot(lightVec2, normalize(tnormal.xyz))/2+0.5;
  // shade = max(shade1, shade2);

  mat4 invVeiwMat = inverse(viewMatrix);
  cameraPos = vec3(invVeiwMat[3][0], invVeiwMat[3][1], invVeiwMat[3][2]);

  worldPos = TMAT[matIndex] * vec4(vertexPos, 1.0);
  worldNormal = TMAT[matIndex] * vec4(vertexNormal, 0.0);
  // vec3 toLightVec = toLight(cameraPos, worldPos.xyz);
  // float diffuse = dot(toLightVec, normalize(tnormal.xyz));

  vec4 relPos = viewMatrix * worldPos;
  vec4 screenPos = projectionMatrix*relPos;

  // shade = diffuse;
  objectColor = vertexColor;
  lightColor = vec4(1, 1, 1, 1);
  gl_Position = screenPos;
}