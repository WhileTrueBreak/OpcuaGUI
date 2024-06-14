#version 430 core

uniform mat4 lightProjectionMatrix;
uniform mat4 lightViewMatrix;

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

out vec3 worldPos;

void main(){
  int matIndex = int(tmatIndex);
  vec4 worldPos4 = (TMAT[matIndex] * vec4(vertexPos, 1.0));
  vec4 relPos = lightViewMatrix * worldPos4;
  worldPos = worldPos4.xyz;
  gl_Position = lightProjectionMatrix * relPos;
}