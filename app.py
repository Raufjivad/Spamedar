import gradio as gr
import transformers
from transformers import pipeline
import tf_keras as keras
import pandas as pd
import tempfile
import os

# Load pre-trained spam classifier
spam_classifier = pipeline(
    "text-classification",
    model="mrm8488/bert-tiny-finetuned-sms-spam-detection"
)

def classify_batch(file):
    """Process uploaded CSV/TXT file with multiple emails"""
    try:
        results = []
        
        # Check if file exists
        if not file.name:
            raise gr.Error("No file uploaded")

        # --- CSV File Handling ---
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
            
            # Check for required email column
            if 'email' not in df.columns:
                raise gr.Error("CSV file must contain a column named 'email'")
                
            emails = df['email'].tolist()

        # --- Text File Handling ---
        elif file.name.endswith('.txt'):
            with open(file.name, 'r') as f:
                emails = f.readlines()
        
        # --- Unsupported Format ---
        else:
            raise gr.Error("Unsupported file format. Only CSV/TXT accepted")

        # Process emails (common for both formats)
        emails = emails[:100]  # Limit to 100 emails
        for email in emails:
            # Handle empty lines in text files
            if not email.strip():
                continue
                
            prediction = spam_classifier(email.strip())[0]
            results.append({
                "email": email.strip()[:50] + "...",
                "label": "SPAM" if prediction["label"] == "LABEL_1" else "HAM",
                "confidence": f"{prediction['score']:.4f}"
            })

        return pd.DataFrame(results)

    except gr.Error as e:
        raise e  # Show pop-up for expected errors
    except Exception as e:
        raise gr.Error(f"Processing error: {str(e)}")

def classify_text(text):
    result = spam_classifier(text)[0]
    return {
        "Spam": result["score"] if result["label"] == "LABEL_1" else 1 - result["score"],
        "Ham": result["score"] if result["label"] == "LABEL_0" else 1 - result["score"]
    }

with gr.Blocks(title="Spam Classifier Pro") as demo:
    gr.Markdown("# 📧 Welcome to Spamedar!")
    
    
    with gr.Tab("✉️ Single Email"):
        gr.Interface(
            description="<h2>Copy your email to find out if it's a is Spam or Ham👇<h2>",
            fn=classify_text,
            inputs=gr.Textbox(label="Input Email", lines=3),
            outputs=gr.Label(label="Classification"),
            examples=[
                ["Urgent: Verify your account details now!"],
                ["Hey, can we meet tomorrow to discuss the project?"],
                ["WINNER! You've been selected for a $1000 Walmart Gift Card!"],
                ["Your account needs verification. Click here to confirm your details."],
                ["Meeting rescheduled to Friday 2 PM"]
            ]
        )
    current_dir = os.getcwd()
    with gr.Tab("📨 Multiple Emails"):
        gr.Markdown("## Upload email batch (CSV or TXT)")
        file_input = gr.File(label="Upload File", file_types=[".csv", ".txt"])
        clear_btn = gr.Button("Clear Selection", variant="secondary")
        output_table = gr.Dataframe(
            headers=["email", "label", "confidence"],
            datatype=["str", "str", "number"],
            interactive=False,
            label="Classification Results"
        )
        download_btn = gr.DownloadButton(label="Download Results")

        def process_file(file):
            """Process file and return (display_df, download_path)"""
            try:
                if file is None:
                    return pd.DataFrame(), None

                results_df = classify_batch(file)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
                    results_df.to_csv(f.name, index=False)
                    return results_df, f.name
            except Exception as e:
                raise gr.Error(f"Error processing file: {str(e)}")

        def clear_selection():
            ###clear file input and results function
            return None, pd.DataFrame(), None
        
        file_input.upload(
            fn=process_file,
            inputs=file_input,
            outputs=[output_table, download_btn]  # Update both components
        )

        clear_btn.click(
            fn=clear_selection,
            outputs=[file_input, output_table, download_btn]
        )

        example_files= [
            os.path.join(os.getcwd(), "sample_emails.csv"),
            os.path.join(os.getcwd(), "batch_emails.txt"),
        ]
        if all(os.path.exists(f) for f in example_files):
            gr.Examples(
                examples=[[f] for f in example_files],
                inputs=file_input,
                outputs=[output_table, download_btn],
                fn=process_file,
                cache_examples=True,
                label="Click any example below to test:"
            )
            
        else:
            print("Warning: Example files missing. Place these in your project root:")
            print("- sample_emails.csv")
            print("- batch_emails.txt")
        
if __name__ == "__main__":
    demo.launch(share=True)
