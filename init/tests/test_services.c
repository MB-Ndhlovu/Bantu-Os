/*
 * Bantu-OS Init System Tests
 * 
 * Basic test stub to verify compilation and basic functionality.
 */

#ifdef TEST_BUILD

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <unistd.h>

/* Include the service code */
#include "../services.c"

/* Test counters */
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) void test_##name(void)
#define RUN_TEST(name) do { \
    printf("Running %s... ", #name); \
    tests_run++; \
    test_##name(); \
    printf("PASSED\n"); \
    tests_passed++; \
} while(0)

#define ASSERT(cond) do { \
    if (!(cond)) { \
        printf("FAILED at %s:%d\n", __FILE__, __LINE__); \
        tests_failed++; \
        return; \
    } \
} while(0)

TEST(service_registry_init) {
    service_registry_init();
    ASSERT(service_count == 0);
    ASSERT(service_list == NULL);
}

TEST(service_register) {
    service_registry_init();
    
    service_t svc = {
        .name = "test_service",
        .exec_path = "/bin/true",
        .priority = PRIORITY_NORMAL,
        .state = SERVICE_STOPPED
    };
    
    int result = service_register(&svc);
    ASSERT(result == 0);
    ASSERT(service_count == 1);
}

TEST(service_find) {
    service_registry_init();
    
    service_t svc = {
        .name = "findme",
        .exec_path = "/bin/false",
        .priority = PRIORITY_NORMAL
    };
    
    service_register(&svc);
    
    service_t *found = service_find("findme");
    ASSERT(found != NULL);
    ASSERT(strcmp(found->name, "findme") == 0);
    
    service_t *not_found = service_find("nonexistent");
    ASSERT(not_found == NULL);
}

TEST(no_duplicate_names) {
    service_registry_init();
    
    service_t svc1 = {
        .name = "duptest",
        .exec_path = "/bin/true",
        .priority = PRIORITY_NORMAL
    };
    
    service_t svc2 = {
        .name = "duptest",
        .exec_path = "/bin/false",
        .priority = PRIORITY_NORMAL
    };
    
    int r1 = service_register(&svc1);
    int r2 = service_register(&svc2);
    
    ASSERT(r1 == 0);
    ASSERT(r2 == -1);
    ASSERT(service_count == 1);
}

TEST(config_parse) {
    service_registry_init();
    
    const char *line = "test_service:50:/bin/test:arg1:arg2";
    service_t svc = {0};
    
    int result = parse_config_line(line, &svc);
    ASSERT(result == 0);
    ASSERT(strcmp(svc.name, "test_service") == 0);
    ASSERT(svc.priority == 50);
    ASSERT(strcmp(svc.exec_path, "/bin/test") == 0);
}

TEST(config_ignore_comments) {
    service_registry_init();
    
    service_t svc = {0};
    
    ASSERT(parse_config_line("# this is a comment", &svc) == -1);
    ASSERT(parse_config_line("; also a comment", &svc) == -1);
}

TEST(state_to_string) {
    ASSERT(strcmp(service_state_str(SERVICE_STOPPED), "STOPPED") == 0);
    ASSERT(strcmp(service_state_str(SERVICE_STARTING), "STARTING") == 0);
    ASSERT(strcmp(service_state_str(SERVICE_RUNNING), "RUNNING") == 0);
    ASSERT(strcmp(service_state_str(SERVICE_STOPPING), "STOPPING") == 0);
    ASSERT(strcmp(service_state_str(SERVICE_FAILED), "FAILED") == 0);
}

TEST(service_unregister) {
    service_registry_init();
    
    service_t svc = {
        .name = "unregtest",
        .exec_path = "/bin/true",
        .priority = PRIORITY_NORMAL
    };
    
    service_register(&svc);
    ASSERT(service_count == 1);
    
    int result = service_unregister("unregtest");
    ASSERT(result == 0);
    ASSERT(service_count == 0);
    ASSERT(service_find("unregtest") == NULL);
}

int main(int argc, char *argv[]) {
    (void)argc;
    (void)argv;
    
    printf("\n=== Bantu-OS Init System Tests ===\n\n");
    
    RUN_TEST(service_registry_init);
    RUN_TEST(service_register);
    RUN_TEST(service_find);
    RUN_TEST(no_duplicate_names);
    RUN_TEST(config_parse);
    RUN_TEST(config_ignore_comments);
    RUN_TEST(state_to_string);
    RUN_TEST(service_unregister);
    
    service_free_registry();
    
    printf("\n=== Test Summary ===\n");
    printf("Tests run:    %d\n", tests_run);
    printf("Tests passed: %d\n", tests_passed);
    printf("Tests failed: %d\n", tests_failed);
    printf("===================\n\n");
    
    return (tests_failed > 0) ? 1 : 0;
}

#else

int main(int argc, char *argv[]) {
    printf("Bantu-OS Init Tests\n");
    printf("Compile with -DTEST_BUILD to run tests.\n");
    printf("\nUsage: gcc -DTEST_BUILD -o test_services test_services.c\n");
    printf("       ./test_services\n");
    return 0;
}

#endif
