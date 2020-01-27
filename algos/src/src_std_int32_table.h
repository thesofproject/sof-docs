/* SRC conversions */
#include <sof/audio/coefficients/src/src_std_int32_3_2_4535_5000.h>
#include <sof/audio/coefficients/src/src_std_int32_7_8_4535_5000.h>
#include <sof/audio/coefficients/src/src_std_int32_21_16_4319_5000.h>
#include <sof/audio/coefficients/src/src_std_int32_21_20_4167_5000.h>
#include <sof/audio/coefficients/src/src_std_int32_21_20_4535_5000.h>

/* SRC table */
int32_t fir_one = 1073741824;
struct src_stage src_int32_1_1_0_0 =  { 0, 0, 1, 1, 1, 1, 1, 0, -1, &fir_one };
struct src_stage src_int32_0_0_0_0 =  { 0, 0, 0, 0, 0, 0, 0, 0,  0, &fir_one };
int src_in_fs[2] = { 32000, 48000};
int src_out_fs[2] = { 44100, 48000};
struct src_stage *src_table1[2][2] = {
	{ &src_int32_21_20_4535_5000, &src_int32_21_20_4167_5000
	},
	{ &src_int32_3_2_4535_5000, &src_int32_1_1_0_0
	}
};
struct src_stage *src_table2[2][2] = {
	{ &src_int32_21_16_4319_5000, &src_int32_7_8_4535_5000
	},
	{ &src_int32_1_1_0_0, &src_int32_1_1_0_0
	}
};
