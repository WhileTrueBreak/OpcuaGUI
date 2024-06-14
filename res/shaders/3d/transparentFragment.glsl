#version 400 core

// shader outputs
layout (location = 0) out vec4 accum;
layout (location = 1) out float reveal;
layout (location = 2) out uvec3 picking;

uniform sampler2D uTextures[%max_textures%];
uniform uint batchId;
uniform samplerCube shadowMap;

flat in uint objIndex;
flat in int texId;
in vec2 texCoord;
in vec4 worldPos;
in vec4 worldNormal;
flat in vec3 cameraPos;
flat in vec3 lightPos;
in vec4 objectColor;
in vec4 lightColor;

// in float shade;
// in vec2 texCoord;
// in vec4 color;

vec3 toV1(vec3 v1, vec3 v2){
  return normalize(v1-v2);
}

void main(){
	if(objectColor.a <= 0.05) discard;
	picking = uvec3(objIndex, batchId, gl_PrimitiveID+1);

	//ambient
	float ambient = 0.35;

	// diffuse
	vec3 toLightVec = toV1(lightPos, worldPos.xyz);
	vec3 toCameraVec = toV1(cameraPos, worldPos.xyz);
  	float diffuse = clamp(dot(toLightVec, normalize(worldNormal.xyz)), 0, 1)*0.8;
	
	//specular
	vec3 halfway = normalize((toLightVec+toV1(cameraPos, worldPos.xyz))/2);
  	float specular = clamp(pow(max(dot(halfway, normalize(worldNormal.xyz)),0.0),16), 0, 1);

	vec4 objColor = vec4(objectColor.xyz*(ambient+diffuse+specular), objectColor.a);

	// weight function
	float weight = clamp(pow(min(1.0, objColor.a * 10.0) + 0.01, 3.0) * 1e8 * pow(1.0 - gl_FragCoord.z * 0.9, 3.0), 1e-2, 3e3);
	accum = vec4(objColor.rgb * objColor.a, objColor.a) * weight;
	reveal = objColor.a;
}