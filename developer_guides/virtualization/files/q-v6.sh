# Assuming "enp2s0" is the name of the network interface, it corresponds
# to the lower ethernet socket on my Up^2. "virbr0" is the bridge, the
# master of both the physical ethernet interface and the virtual network;
# "disk" is a partition, used to store a VM image; "path" is a mount point.
# Note: This is a sample file which you can adjust as necessary. For example,
# if you do not have access to a German keyboard, you may remove the "-k de"
# qemu launch option. Also note that a second instance of the QEMU VNC server
# starts, which then listens on port 5901.

net=enp2s0
vir=virbr0-nic
br=virbr0
ip=<up2-IP-address>

disk=/dev/sda1
path=/var/lib/libvirt/images/

if ! brctl show | grep -q $net; then
	ip link set $net master $br
fi
if ip addr show dev $net | grep -q "$ip/24"; then
	ip addr del $ip/24 dev $net
	dhclient $br
fi
if ! ip addr show dev $vir | grep -q UP; then
	ip link set $vir up
	sleep 0.5
	ip link set $vir master $br
	echo 1 > /proc/sys/net/ipv4/ip_forward
fi
if ! mount | grep -q "$path"; then
	mount $disk $path
fi

modprobe vhost-sof

/usr/bin/qemu-system-x86_64 \
-enable-kvm \
-name guest=ubuntu19.04,debug-threads=on \
-machine pc-q35-4.0,accel=kvm,usb=off,vmport=off,dump-guest-core=off \
-cpu IvyBridge-IBRS,ss=on,vmx=on,movbe=on,hypervisor=on,arat=on,tsc_adjust=on,mpx=on,rdseed=on,smap=on,clflushopt=on,sha-ni=on,umip=on,md-clear=on,stibp=on,arch-capabilities=on,xsaveopt=on,xsavec=on,xgetbv1=on,xsaves=on,pdpe1gb=on,3dnowprefetch=on,rdctl-no=on,skip-l1dfl-vmentry=on,ssb-no=on,mds-no=on,avx=off,f16c=off \
-m 2048 \
-overcommit mem-lock=off \
-smp 2,sockets=2,cores=1,threads=1 \
-uuid 100213e7-1dfd-4a74-a424-ced175df9461 \
-no-user-config \
-nodefaults \
-rtc base=utc,driftfix=slew \
-global kvm-pit.lost_tick_policy=delay \
-no-hpet \
-global ICH9-LPC.disable_s3=1 \
-global ICH9-LPC.disable_s4=1 \
-boot strict=on \
-device pcie-root-port,port=0x10,chassis=1,id=pci.1,bus=pcie.0,multifunction=on,addr=0x2 \
-device pcie-root-port,port=0x11,chassis=2,id=pci.2,bus=pcie.0,addr=0x2.0x1 \
-device pcie-root-port,port=0x12,chassis=3,id=pci.3,bus=pcie.0,addr=0x2.0x2 \
-device pcie-root-port,port=0x13,chassis=4,id=pci.4,bus=pcie.0,addr=0x2.0x3 \
-device pcie-root-port,port=0x14,chassis=5,id=pci.5,bus=pcie.0,addr=0x2.0x4 \
-device pcie-root-port,port=0x15,chassis=6,id=pci.6,bus=pcie.0,addr=0x2.0x5 \
-device ich9-usb-ehci1,id=usb,bus=pcie.0,addr=0x1d.0x7 \
-device ich9-usb-uhci1,masterbus=usb.0,firstport=0,bus=pcie.0,multifunction=on,addr=0x1d \
-device ich9-usb-uhci2,masterbus=usb.0,firstport=2,bus=pcie.0,addr=0x1d.0x1 \
-device ich9-usb-uhci3,masterbus=usb.0,firstport=4,bus=pcie.0,addr=0x1d.0x2 \
-device virtio-serial-pci,id=virtio-serial0,bus=pci.2,addr=0x0 \
-drive file=/var/lib/libvirt/images/ubuntu18.04.qcow2,format=qcow2,if=none,id=drive-virtio-disk0 \
-device virtio-blk-pci,scsi=off,bus=pci.3,addr=0x0,drive=drive-virtio-disk0,id=virtio-disk0,bootindex=1 \
-chardev pty,id=charserial0 \
-device isa-serial,chardev=charserial0,id=serial0 \
-chardev spicevmc,id=charchannel1,name=vdagent \
-device usb-tablet,id=input0,bus=usb.0,port=1 \
-device qxl-vga,id=video0,ram_size=67108864,vram_size=67108864,vram64_size_mb=0,vgamem_mb=16,max_outputs=1,bus=pcie.0,addr=0x1 \
-chardev spicevmc,id=charredir0,name=usbredir \
-device usb-redir,chardev=charredir0,id=redir0,bus=usb.0,port=2 \
-chardev spicevmc,id=charredir1,name=usbredir \
-device usb-redir,chardev=charredir1,id=redir1,bus=usb.0,port=3 \
-device virtio-balloon-pci,id=balloon0,bus=pci.4,addr=0x0 \
-object rng-random,id=objrng0,filename=/dev/urandom \
-device virtio-rng-pci,rng=objrng0,id=rng0,bus=pci.5,addr=0x0 \
-sandbox on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny \
-netdev tap,id=tapnet0,vhost=on,ifname=$vir,script=no,downscript=no \
-device virtio-net-pci,netdev=tapnet0,mac=52:54:00:31:c5:a2,bus=pci.1,addr=0x0 \
-device vhost-dsp-pci,topology=sof-apl-uos0.tplg \
-display vnc="$ip":1 \
-serial stdio \
-k de \
-msg timestamp=on
