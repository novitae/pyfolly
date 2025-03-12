#include <iostream>

#include <folly/Portability.h>
#include <folly/tracing/AsyncStack.h>

// c++ -std=c++20 -fcoroutines -I/opt/homebrew/include -L/opt/homebrew/lib -lfolly test.cpp -o test

int main() {
    #if FOLLY_HAS_COROUTINES
        std::cout << "FOLLY_HAS_COROUTINES = 1\n";
    #else
        std::cout << "FOLLY_HAS_COROUTINES = 0\n";
    #endif
        return 0;
}