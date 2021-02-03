import yaml
import jinja2
import time
from genie.testbed import load

with open("./templates/list_ip.yaml", "r") as file:
    list_ip = yaml.load(file, Loader=yaml.FullLoader)

with open("./templates/list_show.yaml", "r") as file:
    list_show = yaml.load(file, Loader=yaml.FullLoader)

# Where's the folder with my templates (or my folders, if multiple)
template_loader = jinja2.FileSystemLoader(searchpath="./templates")

# Instance of the Environment class. Gives the loader (above), optionally parameters like
# block strings, variable strings etc.
template_env = jinja2.Environment(loader=template_loader)

# Which file is my template
template = template_env.get_template("testbed.tpl")

testbed = load(template.render(list_ip_id = zip(list_ip, range(len(list_ip)))))

# Writting each file
for device in testbed:
    if device.type != "linux":
        device.connect(learn_hostname=True,
                       init_exec_commands=[],
                       init_config_commands=[],
                       log_stdout=False)

        print(f'-- {device.hostname} --')

        with open(f'./outputs/{device.hostname}.txt', 'w') as file:
            #1 Collect the state before (running the collect 2 times to check if it's increasing)
            sod1 = device.execute("show system internal access-list sup-redirect-stats | grep SOD")
            time.sleep(1)
            sod2 = device.execute("show system internal access-list sup-redirect-stats | grep SOD")
            if sod1 != sod2:
                file.write(f'--- SOD Check pass ---\n')
            else:
                file.write(f'--- SOD check is the same -> ACL or lock file here? ---\n')
                file.write('\n\n')
                device.disconnect()
                print('  Skipping due to SOD - done')
                continue

            file.write('\n')

            #2 Copy in bootflash:scripts the script
            #add your script
            if device.execute("show file bootflash:scripts/yourscript md5sum | grep 634aadf02a29b40d6b77621a323b694a | wc lines") != "1":
                file.write(f'--- Copying the script ---\n')
                #Change FTP PASSWORD and IP and SCRIPT
                device.execute("copy ftp://xxxx:yyyy@z.z.z.z//home/yourpath.py bootflash:scripts/yourscript.py vrf management")
                if device.execute("show file bootflash:scripts/yourscript.py md5sum | grep 634aadf02a29b40d6b77621a323b694a | wc lines") != "1":
                    file.write(f'--- Error Copying script ---\n')
                    file.write('\n\n')
                    device.disconnect()
                    print('  ERROR - done')
                    continue
            else:
                file.write(f'--- Script exist ---\n')
                file.write('\n')


            #3 Add the EEM script
            if device.execute("show event manager policy internal dis-shadow | wc lines") != "7":
                file.write(f'--- Copying EEM Script ---\n')
                #Change script name
                device.configure('''
                    event manager applet dis-shadow
                    event syslog pattern ".*System ready.*"
                    action 1.0 cli slot 1 no debug hardware internal tah enable mem-scrub
                    action 2.0 cli slot 1 no debug hardware internal tah enable shadow
                    action 3.0 cli source  yourscript -v
                ''')
                if device.execute("show event manager policy internal dis-shadow | wc lines") != "7":
                    file.write(f'--- Error Configuring EEM ---\n')
                    file.write('\n\n')
                    device.disconnect()
                    print('  ERROR - done')
                    continue
                else:
                    file.write(f'   EEM written successfully\n')
                    file.write('\n')
            else:
                file.write(f'--- EEM exist ---\n')
                file.write('\n')


            #4 Diable mem-scrub
            if "disabled." not in device.execute("slot 1 debug hardware internal tah mem-scrub-error asic 0 | i scan"):
                file.write(f'--- Disabling mem-scrub ---\n')
                device.configure('''
                     slot 1 no debug hardware internal tah enable mem-scrub
                 ''')
                if "disabled." not in device.execute("slot 1 debug hardware internal tah mem-scrub-error asic 0 | i scan"):
                    file.write(f'--- Error disabling mem-scrub ---\n')
                    file.write('\n\n')
                    device.disconnect()
                    print('  ERROR - done')
                    continue
                else:
                    file.write(f'   mem-scrub disabled successfully\n')
                    file.write('\n')
            else:
                file.write(f'--- mem-scrub already disabled ---\n')
                file.write('\n')


            #5 Disable shadow-memory
            if "not enabled" not in device.execute("slot 1 debug hardware internal tah shadow asic 0 | head | grep enable"):
                file.write(f'--- Disabling shadow memory ---\n')
                device.configure('''
                     slot 1 no debug hardware internal tah enable shadow
                 ''')
                if "not enabled" not in device.execute("slot 1 debug hardware internal tah shadow asic 0 | head | grep enable"):
                    file.write(f'--- Error disabling shadow memory ---\n')
                    file.write('\n\n')
                    device.disconnect()
                    print('  ERROR - done')
                    continue
                else:
                    file.write(f'   shadow memory disabled successfully\n')
                    file.write('\n')
            else:
                file.write(f'--- shadow memory already disabled ---\n')
                file.write('\n')

            #6 Install the script
            if device.execute("show system internal access-list tcam ingress start-idx 2814 | egrep drop | uniq") != " drop: 0x1":
                file.write(f'--- installing script ---\n')
                #change script
                device.configure('''
                     source  yourscript -v -d
                 ''')
                if device.execute("show system internal access-list tcam ingress start-idx 2814 | egrep drop | uniq") != " drop: 0x1":
                    file.write(f'--- Error installing script ---\n')
                    file.write('\n\n')
                    device.disconnect()
                    print('  ERROR - done')
                    continue
                else:
                    file.write(f'   script installed successfully\n')
                    file.write('\n')
            else:
                file.write(f'--- script already installed correctly ---\n')
                file.write('\n')

        print('  done')
        device.disconnect()
