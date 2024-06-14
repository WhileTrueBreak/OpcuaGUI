#version 430 core

in vec3 worldPos;

uniform vec3 lightWorldPos;

layout (location = 0) out float lightDistance;

void main(){
  vec3 lightToVertex = worldPos - lightWorldPos;
  lightDistance = length(lightToVertex);
  // lightDistance = gl_FragCoord.x;
}