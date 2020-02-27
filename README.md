# VM templates


# build

Use `packer` with a `var file`
~~~
$ ./packer build --only qemu --var-file=<var_file.json> <template.json>
~~~

Example for `Windows 10`
~~~
$ ./packer build --only qemu --var-file=win10.json windows.json
~~~

# Import in libvirt

Use `import_libvirt.py` to import your generated `qcow` as a defined 
`libvirt` domain.

~~~
# ./import_libvirt.py output_qemu/xxxxx.qcow2
~~~

To specify a custom QEMU, use the `--qemu` switch
~~~
./import_libvirt.py --qemu /home/developer/kvm-vmi/qemu/x86_64-softmmu/qemu-system-x86_64 packer-windows/output-qemu/win7x64
~~~
