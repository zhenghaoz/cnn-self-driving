from loader import DataLoader
from network import PilotNet

if __name__ == '__main__':
    loader = DataLoader('video', mirror=True)
    net = PilotNet(1e-3)
    net.load('model/driver.ckpt')
    net.fit(loader.train_images, loader.train_labels, loader.test_images, loader.test_labels, print_iters=10, iters=100, batch_size=200, epoch=1)
    net.save('model/driver.ckpt')
