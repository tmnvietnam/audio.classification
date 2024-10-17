import os
import io
import logging

import win32pipe
import win32file
import win32con

import librosa
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile

import tensorflow as tf
from sklearn.model_selection import train_test_split

import features
import cfg

WORKING_DIR = ''
MODEL_PATH = ''
HISTORY_IMG_PATH = ''


# Function to plot training and validation accuracy and loss
def plot_training_history(history, filename):
    
    # Plot accuracy
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Train Accuracy')
    plt.plot(history.history['val_accuracy'], label='Val Accuracy')
    plt.title('Training and Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()

    # Plot loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Val Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
  
    plt.savefig(filename)

    # Optionally, close the plot to free memory
    plt.close()

def load_dataset(data_dir, labels):
    audio_data = []
    audio_labels = []
    
    for label in labels:
        folder_path = os.path.join(data_dir, label)
        for file in os.listdir(folder_path):
            if file.endswith('.wav'):
                file_path = os.path.join(folder_path, file)
                # Load the audio file
                audio, _ = librosa.load(file_path, sr=cfg.SAMPLING_RATE)
               
                frequency_features = features.extract_frequency_domain_features(audio, cfg.SAMPLING_RATE)
                time_features = features.extract_time_domain_features(audio, cfg.SAMPLING_RATE)

                combined_features = np.hstack([time_features, frequency_features])                
                combined_features = combined_features /  np.max(combined_features)               


                audio_data.append(combined_features)
                audio_labels.append(labels.index(label))
    
    audio_data = np.array(audio_data)
    audio_labels = np.array(audio_labels)
    return audio_data, audio_labels

# 2. Create a fully connected neural network model
def create_dense_model(input_shape, num_classes):
    model = tf.keras.models.Sequential([
        tf.keras.layers.InputLayer(input_shape=input_shape),
        tf.keras.layers.Dense(300, activation='relu'),
        tf.keras.layers.Dropout(0.5),        
        tf.keras.layers.Dense(100, activation='relu'),
        tf.keras.layers.Dropout(0.6),        
        tf.keras.layers.Dense(num_classes, activation='softmax')
    ])
    
    
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model
    
# 3. Main code to execute training
def train(dataset_path, epochs, batch_size):
    data_dir = dataset_path    
    
    # Load the audio data and extract frequency components using FFT
    X, y = load_dataset(data_dir, cfg.LABELS)    
   
    X = X / np.max(X)  # Scale the features between 0 and 1

    # Split into training and validation sets
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Create the model
    input_shape = (X_train.shape[1],)  # Input shape is based on FFT size
    num_classes = len(cfg.LABELS)
    model = create_dense_model(input_shape, num_classes)       
    
    # Train the model
    history = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=cfg.EPOCHS, batch_size=cfg.BATCH_SIZE)
    
    # Plot training history
    plot_training_history(history, HISTORY_IMG_PATH)

    # Evaluate the model
    test_loss, test_acc = model.evaluate(X_val, y_val, verbose=2)
    print(f"Test accuracy: {test_acc}")
    print(f"Test loss: {test_loss}")

    # Save the model
    model.save(MODEL_PATH)
    
    return test_acc, test_loss

# 4. Load the trained model
def load_model(model_file):
    return tf.keras.models.load_model(model_file)

# 6. Predict the label of a new audio file
def predict_audio_file(file_path, model_file, labels):
    # Load the model
    model = load_model(model_file)       
    
    _, audio_filter = wavfile.read(file_path)
    
    audio, _ = librosa.load(file_path, sr=cfg.SAMPLING_RATE)   

    for i in range(int((2*cfg.T-1)*cfg.N+1)):
        segment_audio = recorded_audio[i*len(recorded_audio)//(int(2*cfg.T*cfg.N)):(i+cfg.N)*len(recorded_audio)//(int(2*cfg.T*cfg.N))]
        # segment_audio_filter = audio_filter[i*len(audio_filter)//(N*4):(i+4)*len(audio_filter)//(N*4)]
        
        frequency_features = features.extract_frequency_domain_features(audio, cfg.SAMPLING_RATE)
        time_features = features.extract_time_domain_features(audio, cfg.SAMPLING_RATE)
        
        # Combine features
        combined_features = np.hstack([time_features, frequency_features])
        
        combined_features = combined_features / np.max(combined_features)
        
        # Reshape the features to match the input shape of the model
        input_data = combined_features.reshape(1, -1)        
        
        # Predict using the trained model
        predictions = model.predict(input_data, verbose=0)
        
        # Return the predicted class
        predicted_label_index = np.argmax(predictions, axis=1)[0]
        
        # Get the label name from the index
        predicted_label = labels[predicted_label_index]       
    
        if (predicted_label == "ok" ):
            return "ok"
            # image = features.plot_wav_to_opencv_image(segment_audio_filter)            
            # filter_result = features.pos_filter(image)
      
            # if filter_result:
            #     return "ok"                 
       
    return "ng"     
        

# 7. Example usage for prediction
def predict(wav_index , model_path, target_label_name):    
    file_name = f'{wav_index}.wav'   
    wave_path = os.path.join(os.path.join(WORKING_DIR, 'audio'), file_name)   

    predicted_label = predict_audio_file(wave_path, model_path, cfg.LABELS)
    return predicted_label == target_label_name

def main():
    global WORKING_DIR
    global MODEL_PATH
    global HISTORY_IMG_PATH
    
    home_directory = os.path.expanduser("~")
    WORKING_DIR = os.path.join(home_directory, ".tensorflow_service")
    os.makedirs(WORKING_DIR, exist_ok=True)
    os.makedirs(os.path.join(WORKING_DIR, "audio"), exist_ok=True)
    
    MODEL_PATH = os.path.join(WORKING_DIR, 'model.h5')    
    HISTORY_IMG_PATH = os.path.join(WORKING_DIR, 'history.png')
    
    while (True):        
        # Create a named pipe
        pipe = win32pipe.CreateNamedPipe(
            cfg.PIPE_NAME,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1, 65536, 65536, 0, None
        )
        
        print("Waiting for next request...")
        win32pipe.ConnectNamedPipe(pipe, None)

        # Read from the pipe
        hr, data = win32file.ReadFile(pipe, 64*1024)
        
        if(data.decode().startswith("init@")):                       
            response = f'response:{WORKING_DIR}'
            win32file.WriteFile(pipe, bytes(response, "utf-8"))
            print(response)
              
        if(data.decode().startswith("predict@")):
            
            wav_index = data.decode().split("@")[1]  
            model_path= data.decode().split("@")[2]              
            
            result = predict(int(wav_index), model_path,"ok") 
            response = f'response:{result}'            
            win32file.WriteFile(pipe, bytes(response, "utf-8"))
            print(response)
            
        if(data.decode().startswith("train@")):
            
            dataset_path = data.decode().split("@")[1]      
            epochs = data.decode().split("@")[2]              
            batch_size = data.decode().split("@")[3]              

            accuracy, loss = train(dataset_path, int(epochs), int(batch_size))
            
            response = f'response:{accuracy}:{loss}'
            win32file.WriteFile(pipe, bytes(response, "utf-8"))
            print(response)
            
        # Clean up
        win32file.CloseHandle(pipe)

if __name__ == "__main__":
    main()