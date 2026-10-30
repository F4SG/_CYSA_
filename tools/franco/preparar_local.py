"""Genera secretos y certificados SOLO en la máquina del equipo. Ejecutar tras ensamblar."""
import argparse,json,os,secrets,subprocess,ipaddress
from pathlib import Path
from datetime import datetime,timedelta,timezone
from cryptography import x509
from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--broker-dns',default='localhost');p.add_argument('--broker-ip',default='127.0.0.1')
    p.add_argument('--public-keycloak',default='http://localhost:8080');p.add_argument('--public-panel',default='http://localhost:8088')
    a=p.parse_args();root=a.repo.resolve();infra=root/'infra';runtime=infra/'runtime'
    if runtime.exists() or (infra/'.env').exists():p.error('Ya existe runtime o .env; no se sobrescriben secretos. Usar otra copia del repositorio.')
    if not (root/'identidad/realm.template.json').is_file():p.error('Falta paquete de Leonardo; ensamblar los tres ZIP primero')
    # Comprobar Docker ANTES de escribir secretos.
    subprocess.run(['docker','version'],check=True,stdout=subprocess.DEVNULL)
    old_umask=os.umask(0o077)
    try:
        mqtt=runtime/'mqtt';mqtt.mkdir(parents=True)
        ca_dir=runtime/'ca-private';ca_dir.mkdir()
        clients=runtime/'clientes';clients.mkdir()
        kc=runtime/'keycloak';kc.mkdir()
        passwords={n:secrets.token_urlsafe(32) for n in ['db','plataforma','deteccion','prueba','emulador','kc_admin','operador','administrador']}
        now=datetime.now(timezone.utc)
        ca_key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        server_key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'CYSA S1 CA local')])
        ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
            .not_valid_after(now+timedelta(days=365)).add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=False,key_encipherment=False,
              data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=False,decipher_only=False),critical=True)
            .sign(ca_key,hashes.SHA256()))
        sans=[x509.DNSName('mosquitto'),x509.DNSName('localhost'),x509.IPAddress(ipaddress.ip_address(a.broker_ip))]
        if a.broker_dns not in ['localhost','mosquitto']:sans.append(x509.DNSName(a.broker_dns))
        cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,a.broker_dns)]))
            .issuer_name(ca.subject).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
            .add_extension(x509.SubjectAlternativeName(sans),critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),critical=False).sign(ca_key,hashes.SHA256()))
        def save_key(path,key):path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        save_key(ca_dir/'ca.key',ca_key);save_key(mqtt/'server.key',server_key)
        (mqtt/'ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM));(mqtt/'server.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        # mosquitto_passwd convierte un archivo local; ninguna contraseña aparece en argumentos de procesos.
        (mqtt/'passwords').write_text(''.join(f'{n}:{passwords[n]}\n' for n in ['deteccion','plataforma','prueba','emulador']),encoding='utf-8')
        image='eclipse-mosquitto:2.0.21'
        subprocess.run(['docker','run','--rm','--user','0:0','--entrypoint','sh','-v',f'{mqtt}:/security',image,'-c',
          'mosquitto_passwd -U /security/passwords && chown -R 1883:1883 /security && chmod 755 /security && chmod 640 /security/server.key /security/passwords && chmod 644 /security/*.crt'],check=True)
        env=f'DB_PASSWORD={passwords["db"]}\nMQTT_PLATAFORMA_PASSWORD={passwords["plataforma"]}\nKC_ADMIN_PASSWORD={passwords["kc_admin"]}\nKEYCLOAK_PUBLIC_URL={a.public_keycloak}\nOIDC_ISSUER={a.public_keycloak}/realms/cysa\n'
        (infra/'.env').write_text(env,encoding='utf-8')
        for n in ['deteccion','prueba','emulador']:
            (clients/f'{n}.env').write_text(f'MQTT_HOST={a.broker_dns}\nMQTT_PORT=8883\nMQTT_CA={mqtt/"ca.crt"}\nMQTT_USER={n}\nMQTT_PASSWORD={passwords[n]}\n',encoding='utf-8')
        realm=json.loads((root/'identidad/realm.template.json').read_text(encoding='utf-8'))
        for client in realm['clients']:
            if client['clientId']=='cysa-panel':
                client['redirectUris']=[a.public_panel+'/'];client['webOrigins']=[a.public_panel];client['attributes']['post.logout.redirect.uris']=a.public_panel+'/'
        realm['users']=[{'username':n,'enabled':True,'emailVerified':True,'firstName':'Administración' if n=='administrador' else 'Operación','lastName':'CYSA',
          'email':n+'@cysa.example','realmRoles':[n],'requiredActions':[],
          'credentials':[{'type':'password','value':passwords[n],'temporary':False}]} for n in ['operador','administrador']]
        (kc/'cysa-realm.json').write_text(json.dumps(realm,indent=2),encoding='utf-8')
        (clients/'usuarios-locales.json').write_text(json.dumps({n:passwords[n] for n in ['operador','administrador']},indent=2),encoding='utf-8')
        config={'apiBase':'/api','issuer':a.public_keycloak+'/realms/cysa','clientId':'cysa-panel','redirectUri':a.public_panel+'/'}
        (root/'panel/config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        from configurar_usuarios_local import prepare_identity_files
        prepare_identity_files(root)
        print('Configuración local generada. Credenciales en infra/runtime/clientes; no compartir ni versionar runtime o .env.')
    finally:os.umask(old_umask)
if __name__=='__main__':main()
