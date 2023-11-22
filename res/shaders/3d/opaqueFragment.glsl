#version 400 core

// shader outputs
layout (location = 0) out vec4 opaque;
layout (location = 1) out uvec3 picking;

uniform sampler2D uTextures[%max_textures%];
uniform uint batchId;

flat in uint objIndex;
flat in int texId;
in float shade;
in vec2 texCoord;
in vec4 color;

void main() {
	// opaque = vec4(float(objIndex), float(batchId), float(gl_PrimitiveID), 1);
	// return;

	if(texId >= 0){
		vec4 color = vec4(color.rgb*shade, color.a); 
		opaque = color * vec4(texture(uTextures[texId], texCoord).rgb, 1);
	}else {
		opaque = vec4(color.rgb*shade, color.a);
	}
	picking = uvec3(objIndex, batchId, gl_PrimitiveID+1);
	// picking = uvec3(objIndex, batchId, 1);
}