"""
凌霄智能影视翻译系统 - 口型同步模块
基于Wav2Lip论文实现

核心功能:
1. 视频帧提取与预处理
2. 音频特征提取
3. 口型生成与混合

参考: "A Lip Sync Expert Is All You Need for Speech to Lip Generation" (2020)
"""

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import Tuple, List, Optional
import tempfile
import subprocess


class Wav2LipInference:
    """
    Wav2Lip推理器
    处理流程:
    1. 视频解码提取帧
    2. 人脸检测与对齐
    3. 音频特征提取
    4. 生成口型
    5. 视频编码输出
    """
    
    def __init__(self, 
                 checkpoint_path: Optional[str] = None,
                 device: str = "cpu"):
        self.device = device
        self.checkpoint_path = checkpoint_path
        self.model = None
        
        # 配置参数
        self.img_size = 96  # 模型输入分辨率
        self.mel_step_size = 16  # 每帧对应的mel帧数
        self.fps = 25  # 视频帧率
        
    def load_model(self):
        """加载Wav2Lip预训练模型"""
        if self.checkpoint_path is None:
            raise ValueError("checkpoint_path is required")
        
        # 创建模型架构
        self.model = Wav2Lip()
        
        # 加载预训练权重
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['state_dict'])
        self.model.to(self.device)
        self.model.eval()
        
    def preprocess_video(self, video_path: str) -> Tuple[List[np.ndarray], dict]:
        """
        视频预处理
        
        Returns:
            frames: 列表，每个元素是 (H, W, 3) 的numpy数组
            info: 视频元信息
        """
        cap = cv2.VideoCapture(video_path)
        
        frames = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)
        
        cap.release()
        
        info = {
            'fps': fps,
            'frame_count': len(frames),
            'original_shape': frames[0].shape if frames else None
        }
        
        return frames, info
    
    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测人脸并返回包围盒
        
        Returns:
            (x1, y1, x2, y2) 或 None
        """
        # 使用OpenCV DNN人脸检测
        # 实际应用中建议使用dlib或MediaPipe获取更精确的关键点
        
        # 简化版本：假设人脸在中央
        h, w = frame.shape[:2]
        face_size = min(h, w) * 0.6
        
        x1 = int((w - face_size) / 2)
        y1 = int((h - face_size) / 2)
        x2 = int(x1 + face_size)
        y2 = int(y1 + face_size)
        
        return (x1, y1, x2, y2)
    
    def crop_face(self, frame: np.ndarray, 
                  bbox: Tuple[int, int, int, int]) -> Tuple[np.ndarray, Tuple]:
        """
        裁剪并预处理人脸区域
        
        Returns:
            face_img: (96, 96, 3) 的标准化人脸图像
            crop_info: 裁剪信息，用于后续恢复
        """
        x1, y1, x2, y2 = bbox
        
        # 扩展到整个头部(包含头发)
        height = y2 - y1
        y1 = max(0, y1 - int(height * 0.5))
        
        # 裁剪
        face_img = frame[y1:y2, x1:x2]
        
        # 调整大小
        face_img_resized = cv2.resize(face_img, (self.img_size * 2, self.img_size * 2))
        
        # 只保留上半部分 (与论文一致的遮挡策略)
        masked_img = face_img_resized.copy()
        masked_img[self.img_size:, :] = 0  # 遮挡下半脸
        
        # 正规化到[-1, 1]
        masked_img = (masked_img.astype(np.float32) / 127.5) - 1.0
        
        crop_info = {
            'bbox': (x1, y1, x2, y2),
            'original_size': (x2-x1, y2-y1)
        }
        
        return masked_img, crop_info
    
    def audio_to_mel(self, audio_path: str) -> np.ndarray:
        """
        将音频转换为Mel谱图
        
        Returns:
            mel: (80, T) 形状的Mel谱图
        """
        # 使用audio_features模块的预处理器
        from .audio_features import AudioPreprocessor
        
        preprocessor = AudioPreprocessor(device=self.device)
        mel = preprocessor(audio_path)
        
        return mel
    
    def generate_lip_sync(self, 
                         face_imgs: List[np.ndarray],
                         mel_chunks: List[np.ndarray]) -> List[np.ndarray]:
        """
        生成口型同步视频
        
        Args:
            face_imgs: 列表，每个是(192, 192, 3)
            mel_chunks: 列表，每个是(80, 16)
            
        Returns:
            gen_faces: 生成的完整人脸列表
        """
        if self.model is None:
            self.load_model()
        
        gen_faces = []
        
        with torch.no_grad():
            for face_img, mel_chunk in zip(face_imgs, mel_chunks):
                # 转tensor
                face_tensor = torch.FloatTensor(face_img).unsqueeze(0).to(self.device)
                face_tensor = face_tensor.permute(0, 3, 1, 2)  # (1, 3, 192, 192)
                
                mel_tensor = torch.FloatTensor(mel_chunk).unsqueeze(0).to(self.device)
                
                # 推理
                gen_face = self.model(mel_tensor, face_tensor)
                
                # 转numpy
                gen_face = gen_face.squeeze(0).permute(1, 2, 0).cpu().numpy()
                gen_face = ((gen_face + 1) * 127.5).astype(np.uint8)
                
                gen_faces.append(gen_face)
        
        return gen_faces
    
    def compose_output(self,
                      original_frames: List[np.ndarray],
                      gen_faces: List[np.ndarray],
                      crop_infos: List[dict]) -> List[np.ndarray]:
        """
        将生成的人脸合成回原始视频
        
        Args:
            original_frames: 原始视频帧
            gen_faces: 生成的人脸
            crop_infos: 裁剪信息
            
        Returns:
            output_frames: 合成后的视频帧
        """
        output_frames = []
        
        for orig_frame, gen_face, crop_info in zip(original_frames, gen_faces, crop_infos):
            x1, y1, x2, y2 = crop_info['bbox']
            orig_h, orig_w = crop_info['original_size']
            
            # 调整回原始大小
            gen_face_resized = cv2.resize(gen_face, (orig_w, orig_h))
            
            # 创建副本
            composed = orig_frame.copy()
            
            # 替换下半脸区域
            face_h = orig_h
            composed[y1:y1+face_h, x1:x2] = gen_face_resized
            
            output_frames.append(composed)
        
        return output_frames
    
    def inference(self, 
                  audio_path: str, 
                  video_path: str,
                  output_path: str):
        """
        完整的推理流程
        """
        print("步骤1: 预处理视频...")
        frames, video_info = self.preprocess_video(video_path)
        
        print("步骤2: 检测人脸...")
        face_imgs = []
        crop_infos = []
        for frame in frames:
            bbox = self.detect_face(frame)
            if bbox:
                face_img, crop_info = self.crop_face(frame, bbox)
                face_imgs.append(face_img)
                crop_infos.append(crop_info)
        
        print("步骤3: 提取音频特征...")
        mel = self.audio_to_mel(audio_path)
        
        # 将mel分割成块 (每帧对应mel_step_size个时间步)
        mel_chunks = []
        for i in range(len(face_imgs)):
            start = int(i * mel.shape[1] / len(face_imgs))
            end = start + self.mel_step_size
            if end <= mel.shape[1]:
                mel_chunks.append(mel[:, start:end])
        
        print("步骤4: 生成口型同步...")
        gen_faces = self.generate_lip_sync(face_imgs, mel_chunks)
        
        print("步骤5: 合成输出视频...")
        output_frames = self.compose_output(frames[:len(gen_faces)], gen_faces, crop_infos)
        
        # 写入输出视频
        self.write_video(output_frames, audio_path, output_path, video_info['fps'])
        
        print(f"完成! 输出: {output_path}")
        
    def write_video(self, frames: List[np.ndarray], 
                   audio_path: str, 
                   output_path: str,
                   fps: float):
        """使用FFmpeg写入视频"""
        # 创建临时视频文件
        temp_video = tempfile.mktemp(suffix='.avi')
        
        # 写入视频帧
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (w, h))
        
        for frame in frames:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
        out.release()
        
        # 使用FFmpeg合并音频
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_video,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        subprocess.run(cmd, capture_output=True)
        
        # 清理临时文件
        Path(temp_video).unlink(missing_ok=True)


class Wav2Lip(nn.Module):
    """
    Wav2Lip 模型架构
    简化版本用于教育演示
    """
    
    def __init__(self):
        super().__init__()
        
        # Audio Encoder
        self.audio_encoder = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Conv2d(32, 32, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        
        # Face Encoder
        self.face_encoder = nn.Sequential(
            nn.Conv2d(6, 16, kernel_size=7, stride=1, padding=3),  # 3通道输入，另外3通道mask
            nn.BatchNorm2d(16),
            nn.ReLU(),
            
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            
            nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            
            nn.ConvTranspose2d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            
            nn.Conv2d(32, 3, kernel_size=7, stride=1, padding=3),
            nn.Tanh()
        )
    
    def forward(self, audio_mel: torch.Tensor, face_img: torch.Tensor) -> torch.Tensor:
        """
        Args:
            audio_mel: (B, 1, 80, 16)
            face_img: (B, 3, 192, 192)
        
        Returns:
            gen_face: (B, 3, 192, 192)
        """
        # Audio encoding
        audio_feat = self.audio_encoder(audio_mel)  # (B, 128, 10, 2)
        
        # Face encoding - 创建mask通道
        B, C, H, W = face_img.shape
        mask = torch.zeros(B, 3, H, W, device=face_img.device)
        # 下半部分为mask区域
        mask[:, :, H//2:, :] = 1
        face_with_mask = torch.cat([face_img, mask], dim=1)  # (B, 6, H, W)
        
        face_feat = self.face_encoder(face_with_mask)  # (B, 128, 24, 24)
        
        # 特征融合 (音频特征扩展到面部空间)
        audio_feat = F.interpolate(audio_feat, size=(24, 24), mode='bilinear')
        fused_feat = torch.cat([face_feat, audio_feat], dim=1)
        
        # Decode
        gen_face = self.decoder(fused_feat)
        
        return gen_face


if __name__ == "__main__":
    print("测试Wav2Lip模型...")
    
    model = Wav2Lip()
    
    # 测试输入
    audio_mel = torch.randn(1, 1, 80, 16)
    face_img = torch.randn(1, 3, 192, 192)
    
    output = model(audio_mel, face_img)
    
    print(f"输入音频特征: {audio_mel.shape}")
    print(f"输入面部图像: {face_img.shape}")
    print(f"输出合成面部: {output.shape}")
    print("模型结构测试通过!")
