#include <jni.h>
#include <android/log.h>
#include <atomic>
#include <functional>
#include <ostream>
#include <streambuf>
#include <string>

#include "llm/llm.hpp"

#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, "MnnLlmJNI", __VA_ARGS__)
using MNN::Transformer::Llm;

namespace {
struct Session {
    Llm* llm = nullptr;
    std::atomic<bool> stop{false};
};

std::string toString(JNIEnv* env, jstring value) {
    if (!value) return {};
    const char* chars = env->GetStringUTFChars(value, nullptr);
    std::string result = chars ? chars : "";
    if (chars) env->ReleaseStringUTFChars(value, chars);
    return result;
}

std::string toUtf8(JNIEnv* env, jbyteArray value) {
    if (!value) return {};
    const jsize size = env->GetArrayLength(value);
    std::string result(static_cast<size_t>(size), '\0');
    if (size > 0) env->GetByteArrayRegion(value, 0, size, reinterpret_cast<jbyte*>(&result[0]));
    return result;
}

size_t completeUtf8Prefix(const std::string& value) {
    const size_t n = value.size();
    size_t i = n;
    for (int back = 0; i > 0 && back < 4; ++back) {
        --i;
        const unsigned char c = static_cast<unsigned char>(value[i]);
        if ((c & 0xC0) == 0x80) continue;
        const size_t need = c >= 0xF0 ? 4 : c >= 0xE0 ? 3 : c >= 0xC0 ? 2 : 1;
        return n - i >= need ? n : i;
    }
    return n;
}

class CallbackBuf final : public std::streambuf {
public:
    explicit CallbackBuf(std::function<bool(const std::string&)> callback)
        : callback_(std::move(callback)) {}
    void flushAll() {
        if (!pending_.empty()) {
            callback_(pending_);
            pending_.clear();
        }
    }
protected:
    std::streamsize xsputn(const char* s, std::streamsize n) override {
        push(std::string(s, static_cast<size_t>(n)));
        return n;
    }
    int_type overflow(int_type c) override {
        if (!traits_type::eq_int_type(c, traits_type::eof()))
            push(std::string(1, traits_type::to_char_type(c)));
        return traits_type::not_eof(c);
    }
private:
    void push(const std::string& chunk) {
        pending_ += chunk;
        const size_t count = completeUtf8Prefix(pending_);
        if (count > 0) {
            callback_(pending_.substr(0, count));
            pending_.erase(0, count);
        }
    }
    std::function<bool(const std::string&)> callback_;
    std::string pending_;
};
} // namespace

extern "C" JNIEXPORT jlong JNICALL
Java_com_seankew_mnnllm_MnnLlm_nativeCreate(JNIEnv* env, jobject, jstring configPath, jstring extraConfig) {
    try {
        Llm* llm = Llm::createLLM(toString(env, configPath));
        if (!llm) return 0;
        const std::string extra = toString(env, extraConfig);
        if (!extra.empty()) llm->set_config(extra);
        llm->load();
        auto* session = new Session();
        session->llm = llm;
        return reinterpret_cast<jlong>(session);
    } catch (const std::exception& error) {
        LOGE("nativeCreate failed: %s", error.what());
        return 0;
    }
}

extern "C" JNIEXPORT jint JNICALL
Java_com_seankew_mnnllm_MnnLlm_nativeGenerate(JNIEnv* env, jobject, jlong handle,
        jobjectArray roles, jobjectArray contents, jint maxNewTokens, jobject callback) {
    auto* session = reinterpret_cast<Session*>(handle);
    if (!session || !session->llm || !callback) return -1;
    session->stop = false;
    jclass callbackClass = env->GetObjectClass(callback);
    jmethodID onToken = env->GetMethodID(callbackClass, "onToken", "([B)Z");
    if (!onToken) return -2;

    try {
        MNN::Transformer::ChatMessages messages;
        const jsize count = env->GetArrayLength(roles);
        for (jsize i = 0; i < count; ++i) {
            auto role = static_cast<jstring>(env->GetObjectArrayElement(roles, i));
            auto bytes = static_cast<jbyteArray>(env->GetObjectArrayElement(contents, i));
            messages.emplace_back(toString(env, role), toUtf8(env, bytes));
            env->DeleteLocalRef(role);
            env->DeleteLocalRef(bytes);
        }

        CallbackBuf buffer([&](const std::string& piece) {
            jbyteArray bytes = env->NewByteArray(static_cast<jsize>(piece.size()));
            env->SetByteArrayRegion(bytes, 0, static_cast<jsize>(piece.size()),
                    reinterpret_cast<const jbyte*>(piece.data()));
            const jboolean keepGoing = env->CallBooleanMethod(callback, onToken, bytes);
            env->DeleteLocalRef(bytes);
            if (env->ExceptionCheck()) {
                env->ExceptionClear();
                session->stop = true;
                return false;
            }
            if (keepGoing != JNI_TRUE) session->stop = true;
            return keepGoing == JNI_TRUE;
        });
        std::ostream output(&buffer);

        session->llm->reset();
        session->llm->response(messages, &output, nullptr, 1);
        auto context = session->llm->getContext();
        while (!session->stop && !session->llm->stoped() && context->gen_seq_len < maxNewTokens) {
            session->llm->generate(1);
        }
        buffer.flushAll();
        output.flush();
        env->DeleteLocalRef(callbackClass);
        return context->gen_seq_len;
    } catch (const std::exception& error) {
        LOGE("nativeGenerate failed: %s", error.what());
        env->DeleteLocalRef(callbackClass);
        return -3;
    }
}

extern "C" JNIEXPORT void JNICALL
Java_com_seankew_mnnllm_MnnLlm_nativeStop(JNIEnv*, jobject, jlong handle) {
    auto* session = reinterpret_cast<Session*>(handle);
    if (session) session->stop = true;
}

extern "C" JNIEXPORT void JNICALL
Java_com_seankew_mnnllm_MnnLlm_nativeReset(JNIEnv*, jobject, jlong handle) {
    auto* session = reinterpret_cast<Session*>(handle);
    if (session && session->llm) session->llm->reset();
}

extern "C" JNIEXPORT void JNICALL
Java_com_seankew_mnnllm_MnnLlm_nativeRelease(JNIEnv*, jobject, jlong handle) {
    auto* session = reinterpret_cast<Session*>(handle);
    if (!session) return;
    if (session->llm) Llm::destroy(session->llm);
    delete session;
}
