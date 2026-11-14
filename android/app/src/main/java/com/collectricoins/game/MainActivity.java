package com.collectricoins.game;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebChromeClient;
import android.webkit.WebViewClient;
import android.webkit.ValueCallback;

import androidx.webkit.WebViewAssetLoader;

public final class MainActivity extends Activity {
    private static final String APP_HOST = "appassets.androidplatform.net";
    private static final String APP_URL =
            "https://" + APP_HOST + "/assets/www/index.html?android=1";
    private static final int IMAGE_PICKER_REQUEST = 1;

    private WebView webView;
    private ValueCallback<Uri[]> imageUploadCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(131, 217, 243));
        getWindow().setNavigationBarColor(Color.rgb(242, 248, 255));

        WebViewAssetLoader assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(242, 248, 255));
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setSupportZoom(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                if (imageUploadCallback != null) {
                    imageUploadCallback.onReceiveValue(null);
                }
                imageUploadCallback = filePathCallback;
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("image/*");
                try {
                    startActivityForResult(intent, IMAGE_PICKER_REQUEST);
                    return true;
                } catch (ActivityNotFoundException exception) {
                    imageUploadCallback = null;
                    filePathCallback.onReceiveValue(null);
                    return false;
                }
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(
                    WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(
                    WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"https".equals(uri.getScheme()) || !APP_HOST.equals(uri.getHost());
            }
        });

        setContentView(webView, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        webView.loadUrl(APP_URL);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != IMAGE_PICKER_REQUEST || imageUploadCallback == null) {
            return;
        }
        Uri selectedImage = resultCode == RESULT_OK && data != null ? data.getData() : null;
        imageUploadCallback.onReceiveValue(
                selectedImage == null ? null : new Uri[]{selectedImage});
        imageUploadCallback = null;
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
