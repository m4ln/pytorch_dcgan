# IMPORTS
import sys
from pathlib import Path

import numpy as np
import torch.nn as nn
import torch.backends.cudnn as cudnn
import torch.optim as optim
import torch.utils.data
import torchvision.datasets as dset
import torchvision.transforms as transforms
import torchvision.utils as vutils

import utils
from dcgan import Generator, Discriminator, weights_init

if __name__ == "__main__":
    # HYPERPARAMETERS
    # True for GPU training, False for CPU training
    CUDA = True
    # path to project
    project_name = 'glomerulus'
    class_name = '05'
    PROJECT_PATH = Path('D:/pytorch_dcgan')
    # path to input date
    IN_PATH = PROJECT_PATH.joinpath('input', project_name, class_name)
    # path to store output files
    OUT_PATH = PROJECT_PATH.joinpath('output', project_name, class_name, 'train')
    # number of images in one batch, adjust this value according to your GPU memory
    BATCH_SIZE = 128
    # number if epochs for training (increase value for better results)
    EPOCH_NUM = 500
    # learning rate (increase value for better results)
    LR = 2e-4
    # number of channels, 1 for grayscale, 3 for rgb image
    IMAGE_CHANNEL = 3
    Z_DIM = 100
    X_DIM = 64
    G_HIDDEN = X_DIM
    D_HIDDEN = G_HIDDEN
    # labels for classification (1=real, 0=fake)
    REAL_LABEL = 1
    FAKE_LABEL = 0
    # Change to None to get different results at each run
    SEED = 1

    # create log file and write outputs
    LOG_FILE = OUT_PATH.joinpath('log.txt')
    utils.clear_folder(OUT_PATH)
    print("Logging to {}\n".format(LOG_FILE))
    sys.stdout = utils.StdOut(LOG_FILE)
    CUDA = CUDA and torch.cuda.is_available()
    print("PyTorch version: {}".format(torch.__version__))
    if CUDA:
        print("CUDA version: {}\n".format(torch.version.cuda))

    if SEED is None:
        SEED = np.random.randint(1, 10000)
    print("Random Seed: {}\n".format(SEED))
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if CUDA:
        torch.cuda.manual_seed(SEED)
    cudnn.benchmark = True      # May train faster but cost more memory

    # training parameters
    print("Learning rate: {}".format(LR))
    print("Batch size: {}".format(BATCH_SIZE))
    print("Epochs: {}\n".format(EPOCH_NUM))

    # load dataset
    if IN_PATH.exists():
        dataset = dset.ImageFolder(root=IN_PATH,
                                   transform=transforms.Compose([
                                       transforms.Resize(X_DIM),
                                       transforms.CenterCrop(X_DIM),
                                       # transforms.RandomHorizontalFlip(),
                                       # transforms.RandomVerticalFlip(),
                                       # transforms.RandomRotation(180),
                                       transforms.ToTensor(),
                                       transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
                                   ]))
    else:
        print("no data available, using MNIST dataset instead")
        IMAGE_CHANNEL = 1
        IN_PATH = PROJECT_PATH.joinpath('input/mnist/mnist')
        dataset = dset.MNIST(root=IN_PATH, download=True,
                             transform=transforms.Compose([
                                 transforms.Resize(X_DIM),
                                 transforms.ToTensor(),
                                 transforms.Normalize((0.5,), (0.5,))
                             ]))

    assert dataset
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE,
                                             shuffle=True, num_workers=4)

    print("Number of training images: {}\n".format(len(dataset)))

    # init GPU or CPU
    device = torch.device("cuda:0" if CUDA else "cpu")

    # Generator
    netG = Generator(IMAGE_CHANNEL, Z_DIM, G_HIDDEN).to(device)
    netG.apply(weights_init)
    print(netG)

    # Discriminator
    netD = Discriminator(IMAGE_CHANNEL, D_HIDDEN).to(device)
    netD.apply(weights_init)
    print(netD)

    # loss function
    criterion = nn.BCELoss()
    # criterion = nn.BCEWithLogitsLoss()

    viz_noise = torch.randn(BATCH_SIZE, Z_DIM, 1, 1, device=device)

    # optimizer
    optimizerD = optim.Adam(netD.parameters(), lr=LR, betas=(0.5, 0.999))
    optimizerG = optim.Adam(netG.parameters(), lr=LR, betas=(0.5, 0.999))

    for epoch in range(EPOCH_NUM):
        for i, data in enumerate(dataloader):
            x_real = data[0].to(device)
            real_label = torch.full((x_real.size(0),), REAL_LABEL, dtype=torch.float32, device=device)
            fake_label = torch.full((x_real.size(0),), FAKE_LABEL, dtype=torch.float32, device=device)

            # Update D with real data
            netD.zero_grad()
            y_real = netD(x_real)
            loss_D_real = criterion(y_real, real_label)
            loss_D_real.backward()

            # Update D with fake data
            z_noise = torch.randn(x_real.size(0), Z_DIM, 1, 1, device=device)
            x_fake = netG(z_noise)
            y_fake = netD(x_fake.detach())
            loss_D_fake = criterion(y_fake, fake_label)
            loss_D_fake.backward()
            optimizerD.step()

            # Update G with fake data
            netG.zero_grad()
            y_fake_r = netD(x_fake)
            loss_G = criterion(y_fake_r, real_label)
            loss_G.backward()
            optimizerG.step()

            if i % 100 == 0:
                print('Epoch {} [{}/{}] loss_D_real: {:.4f} loss_D_fake: {:.4f} loss_G: {:.4f}'.format(
                    epoch, i, len(dataloader),
                    loss_D_real.mean().item(),
                    loss_D_fake.mean().item(),
                    loss_G.mean().item()
                ))
                vutils.save_image(x_real, OUT_PATH.joinpath('real_samples.png'), normalize=True)
                with torch.no_grad():
                    viz_sample = netG(viz_noise)
                    vutils.save_image(viz_sample, OUT_PATH.joinpath('fake_samples_{}.png'.format(epoch)), normalize=True)
        torch.save(netG.state_dict(), OUT_PATH.joinpath('netG_{}.pth'.format(epoch)))
        torch.save(netD.state_dict(), OUT_PATH.joinpath('netD_{}.pth'.format(epoch)))
