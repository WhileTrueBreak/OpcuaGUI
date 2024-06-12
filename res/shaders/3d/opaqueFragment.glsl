#version 400 core

// shader outputs
layout (location = 0) out vec4 opaque;
layout (location = 1) out uvec3 picking;

uniform sampler2D uTextures[%max_textures%];
uniform uint batchId;

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
// in vec4 color;

vec3 toV1(vec3 v1, vec3 v2){
  return normalize(v1-v2);
}

float distsq(vec3 v1, vec3 v2){
	vec3 c = v1-v2;
	return dot(c, c);
}

void main() {
	picking = uvec3(objIndex, batchId, gl_PrimitiveID+1);

	//ambient
	float ambient = 0.2;

	// diffuse
	vec3 toLightVec = toV1(lightPos, worldPos.xyz);
	vec3 toCameraVec = toV1(cameraPos, worldPos.xyz);
  	float diffuse = dot(toLightVec, normalize(worldNormal.xyz));
	
	//specular
	vec3 halfway = normalize((toLightVec+toCameraVec)/2);
  	float specular = pow(max(dot(halfway, normalize(worldNormal.xyz)),0.0),16);

	vec3 ambientColor = vec3(objectColor.xyz*ambient);
	vec3 diffuseColor = vec3(objectColor.xyz*diffuse);
	vec3 specularColor = vec3(objectColor.xyz*specular);

	opaque = vec4(objectColor.xyz*min(ambient+diffuse+specular, 1), 1);



	// opaque = vec4(float(objIndex), float(batchId), float(gl_PrimitiveID), 1);
	// return;

	// if(texId >= 0){
	// 	vec4 color = vec4(color.rgb*shade, color.a); 
	// 	opaque = color * vec4(texture(uTextures[texId], texCoord).rgb, 1);
	// }else {
	// 	opaque = vec4(color.rgb*shade, color.a);
	// }
	// picking = uvec3(objIndex, batchId, 1);
}