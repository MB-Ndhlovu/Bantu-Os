/*
 * bantu_os/init/tests/test_services.c
 * Basic unit tests for service registry.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <assert.h>

#include "../services.h"

static int test_callback_called = 0;

int test_on_start(void)
{
    test_callback_called++;
    return 0;
}

int test_on_stop(void)
{
    test_callback_called--;
    return 0;
}

void test_registry_init(void)
{
    printf("[test] test_registry_init...\n");
    service_registry_init();
    assert(service_count() == 0);
    printf("[test] PASS\n");
}

void test_service_register(void)
{
    printf("[test] test_service_register...\n");
    service_registry_init();

    service_t svc = {0};
    strcpy(svc.name, "test_svc");
    strcpy(svc.exec_path, "/bin/true");
    svc.priority = PRIORITY_NORMAL;
    svc.restart_policy = RESTART_NONE;

    int ret = service_register(&svc);
    assert(ret == 0);
    assert(service_count() == 1);

    service_t *found = service_find("test_svc");
    assert(found != NULL);
    assert(strcmp(found->name, "test_svc") == 0);

    printf("[test] PASS\n");
}

void test_service_find(void)
{
    printf("[test] test_service_find...\n");
    service_registry_init();

    service_t svc1 = {0}, svc2 = {0};
    strcpy(svc1.name, "svc1");
    strcpy(svc1.exec_path, "/bin/true");
    svc1.priority = PRIORITY_NORMAL;

    strcpy(svc2.name, "svc2");
    strcpy(svc2.exec_path, "/bin/false");
    svc2.priority = PRIORITY_EARLY;

    service_register(&svc1);
    service_register(&svc2);

    assert(service_find("svc1") != NULL);
    assert(service_find("svc2") != NULL);
    assert(service_find("nonexistent") == NULL);

    printf("[test] PASS\n");
}

void test_callbacks(void)
{
    printf("[test] test_callbacks...\n");
    service_registry_init();
    test_callback_called = 0;

    service_t svc = {0};
    strcpy(svc.name, "callback_test");
    strcpy(svc.exec_path, "/bin/true");
    svc.priority = PRIORITY_NORMAL;
    svc.on_start = test_on_start;
    svc.on_stop = test_on_stop;

    service_register(&svc);
    service_t *found = service_find("callback_test");
    assert(found != NULL);
    assert(found->on_start != NULL);
    assert(found->on_stop != NULL);

    printf("[test] PASS\n");
}

void test_parse_config_line(void)
{
    printf("[test] test_parse_config_line...\n");
    service_registry_init();

    service_t svc = {0};
    int ret = parse_config_line("syslog:10:/sbin/syslogd", &svc);
    assert(ret == 0);
    assert(strcmp(svc.name, "syslog") == 0);
    assert(svc.priority == 10);
    assert(strcmp(svc.exec_path, "/sbin/syslogd") == 0);

    printf("[test] PASS\n");
}

void test_state_transitions(void)
{
    printf("[test] test_state_transitions...\n");

    assert(strcmp(service_state_str(SERVICE_STOPPED), "STOPPED") == 0);
    assert(strcmp(service_state_str(SERVICE_RUNNING), "RUNNING") == 0);
    assert(strcmp(service_state_str(SERVICE_FAILED), "FAILED") == 0);

    assert(strcmp(service_priority_str(PRIORITY_CRITICAL), "CRITICAL") == 0);
    assert(strcmp(service_priority_str(PRIORITY_NORMAL), "NORMAL") == 0);

    printf("[test] PASS\n");
}

int main(void)
{
    printf("=== Bantu-OS service registry tests ===\n");

    test_registry_init();
    test_service_register();
    test_service_find();
    test_callbacks();
    test_parse_config_line();
    test_state_transitions();

    service_free_registry();

    printf("\n=== ALL TESTS PASSED ===\n");
    return 0;
}