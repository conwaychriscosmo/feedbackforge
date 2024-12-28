from feedback_forge_sdk.sdk import DocumentProcessingSDK

sdk = DocumentProcessingSDK(config_path="env.yaml")
sdk.authenticate()

test_urls = [
    "https://example.com/document1.pdf",
    "https://example.com/document2.pdf"
]

results = sdk.process_documents(urls=test_urls)
for result in results:
    print(f"Document {result.url}: {result.status}")
