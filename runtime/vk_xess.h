#pragma once
#include <stdint.h>
#include "vk.h"

#ifdef __cplusplus
extern "C" {
#endif

// Intel XeSS (Xe Super Sampling) & Intel Xe Stack
int vk_xess_wanted(void);
int vk_xess_available(void);
int vk_xefg_available(void);
int vk_xell_available(void);
int vk_xess_is_xmx(void);
const char *vk_xess_model_name(void);
uint64_t vk_xess_dispatches(void);
void vk_xess_init(void);
void vk_xess_release(void);

typedef struct VkExec VkExec;
void vk_xess_pass(VkExec *ex);
void vk_xess_frame(void);

#ifdef __cplusplus
}
#endif
