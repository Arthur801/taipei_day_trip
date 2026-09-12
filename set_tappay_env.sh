#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "請使用 source set_tappay_env.sh 執行此程式。"
    exit 1
fi

read -r -s -p "TapPay Partner Key: " tappay_partner_key
printf "\n"
read -r -p "TapPay Merchant ID: " tappay_merchant_id

if [[ -z "${tappay_partner_key}" || -z "${tappay_merchant_id}" ]]; then
    unset tappay_partner_key tappay_merchant_id
    echo "Partner Key 與 Merchant ID 不可為空。"
    return 1
fi

export TAPPAY_PARTNER_KEY="${tappay_partner_key}"
export TAPPAY_MERCHANT_ID="${tappay_merchant_id}"
unset tappay_partner_key tappay_merchant_id

echo "TapPay 後端環境變數已設定，請在目前的 shell 啟動 FastAPI。"
