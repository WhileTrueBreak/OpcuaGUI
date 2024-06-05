#version 400 core

// shader outputs
layout (location = 0) out vec4 frag;
layout (location = 1) out uvec3 oPicking;

uniform vec2 texture_dim;
in vec2 texPos;

uniform sampler2D screen;
uniform usampler2D picking;
uniform sampler2D depth;

float linearize_depth(float d,float zNear,float zFar) {
	// return (1/(d*(1/zFar-1/zNear)+1/zNear)-zNear)/(zFar-zNear);
	return (d*zNear)/(zFar+d*zNear-d*zFar);
}

bool is_edge(ivec2 coords){

	uvec3 v0 = texelFetch(picking, coords, 0).xyz;
	oPicking = v0;

	uvec2 v1 = texelFetch(picking, ivec2(coords.x+1, coords.y), 0).xy;
	uvec2 v2 = texelFetch(picking, ivec2(coords.x-1, coords.y), 0).xy;
	uvec2 v3 = texelFetch(picking, ivec2(coords.x, coords.y+1), 0).xy;
	uvec2 v4 = texelFetch(picking, ivec2(coords.x, coords.y-1), 0).xy;

	float dist = max(max(length(v0.xy-v1), length(v0.xy-v2)),max(length(v0.xy-v3), length(v0.xy-v4)));
	return dist > 0.01;
}

float get_normalised_depth(vec2 res){
	float d = texture(depth, res).x;
	if (d != 1) {
		d = linearize_depth(d, 0.01, 100);
	}
	return 1-d;
}

vec4 pixelate(vec2 coords, float pixel_size) {
	ivec2 pp = ivec2(floor(coords/pixel_size)*pixel_size);
	return texelFetch(screen, pp, 0);
}


void main() {
	ivec2 coords = ivec2(gl_FragCoord.xy);
	vec2 res = gl_FragCoord.xy / texture_dim;
	float d = get_normalised_depth(res);

	frag = texture(screen, res)*d;

}