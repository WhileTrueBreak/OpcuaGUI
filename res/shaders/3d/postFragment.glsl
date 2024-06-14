#version 400 core
#define PI 3.1415926538

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

vec4 vec4pow(vec4 a){
	return vec4(a.x*a.x, a.y*a.y, a.z*a.z, a.w*a.w);
}

vec4 pixelate(vec2 coords, float pixel_size) {
	ivec2 pp = ivec2(floor(coords/pixel_size)*pixel_size);
	vec4 c1 = vec4pow(texelFetch(screen, pp, 0))*0.25;
	vec4 c2 = vec4pow(texelFetch(screen, pp+ivec2(0,pixel_size), 0))*0.25;
	vec4 c3 = vec4pow(texelFetch(screen, pp+ivec2(pixel_size,0), 0))*0.25;
	vec4 c4 = vec4pow(texelFetch(screen, pp+ivec2(pixel_size,pixel_size), 0))*0.25;
	return sqrt(c1+c2+c3+c4);
}

vec4 abb(vec2 res, float dist) {
	vec4 color = texture(screen, res);
	float r = texture(screen, res+vec2(dist/texture_dim.x,0)).r;
	if(res.x+dist/texture_dim.x >= 1) {
		r = color.r;
	}
	float g = color.g;
	float b = texture(screen, res-vec2(dist/texture_dim.x,0)).b;
	if(res.x-dist/texture_dim.x <= 0) {
		b = color.b;
	}
	return vec4(r,g,b,1);
	// return texture(screen, res);
}

float dist_sq(vec2 a, vec2 b){
	vec2 c = (a-b)*2;
	return dot(c,c);
}

vec2 quad_distort(vec2 p, float f, float zoom){
	return vec2(
		(p.x-0.5)*(f*pow(2*p.y-1, 2.)+1)*zoom+0.5,
		(p.y-0.5)*(f*pow(2*p.x-1, 2.)+1)*zoom+0.5
	);
}

float srgb2linear(float x){
	if(x < 0.04045) return x/12.92;
	return pow((x+0.055)/1.055, 2.4);
}

float srgb2grey(vec3 rgb){
	return srgb2linear(rgb.r)*0.2126+srgb2linear(rgb.g)*0.7152+srgb2linear(rgb.b)*0.0722;
}

float quantize(float grey, int num){
	if(grey >= 1) return 1.0;
	return floor(grey*num)/(num-1);
}

int quantizeindex(float grey, int num){
	if(grey >= 1) return (num-1);
	return int(grey*num);
}

vec3 rgb2hsv(vec3 c){
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));

    float d = q.x - min(q.w, q.y);
    float e = 1.0e-10;
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c){
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

vec3 palette(float hs, float hstep, float s, float vs, float vstep, int index){
	return hsv2rgb(vec3(hs+hstep*index, s, vs+vstep*index));
}

void main() {
	ivec2 coords = ivec2(gl_FragCoord.xy);
	vec2 res = gl_FragCoord.xy / texture_dim;
	vec4 color = texture(screen, res);

	// float d = get_normalised_depth(res);
	// float nd = 1-d;

	// float dist = dist_sq(res, vec2(0.5,0.5));
	// vec2 distort_res = quad_distort(res, 0.15, 0.85);
	// float xoff = pow(sin((distort_res.y*texture_dim.y+2)*PI/16), 4.)/1*dist;
	// float brightness = sin(distort_res.y*texture_dim.y*PI/4)+1;
	// if(brightness > 1) brightness = 1;
	// if(brightness < 0.8) brightness = 0.9;

	// xoff = xoff/texture_dim.x;
	// float resoff = res.x+xoff;
	// if(resoff <= 0) xoff = 0;
	// if(resoff >= 1) xoff = 0;
	// res = vec2(distort_res.x+xoff, distort_res.y);

	float grey = clamp(srgb2grey(color.rgb),0,1);
	int colorindex = quantizeindex(grey, 8);
	vec3 palettecolor = palette(0.65, 0.02, 0.5, 0.6, 0.03, colorindex);
	frag = vec4(palettecolor, 1);
	frag = color;

}