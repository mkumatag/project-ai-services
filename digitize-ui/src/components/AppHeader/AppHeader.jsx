import {
  Header,
  HeaderName,
  HeaderGlobalBar,
  HeaderGlobalAction,
  HeaderMenuButton,
  Theme,
} from '@carbon/react';
import { Help, Notification } from '@carbon/icons-react';
import styles from './AppHeader.module.scss';

const AppHeader = ({ isSideNavOpen, setIsSideNavOpen }) => {
  return (
    <Theme theme="g100">
      <Header aria-label="IBM Digitize Service">
        <HeaderMenuButton
          aria-label="Open menu"
          onClick={(e) => {
            e.stopPropagation();
            setIsSideNavOpen((prev) => !prev);
          }}
          isActive={isSideNavOpen}
          isCollapsible
          className={styles.menuBtn}
        />

        <HeaderName prefix="IBM">Digitize Service</HeaderName>

        <HeaderGlobalBar>
          <HeaderGlobalAction aria-label="Help" className={styles.iconWidth}>
            <Help size={20} />
          </HeaderGlobalAction>

          <HeaderGlobalAction
            aria-label="Notifications"
            className={styles.iconWidth}
          >
            <Notification size={20} />
          </HeaderGlobalAction>
        </HeaderGlobalBar>
      </Header>
    </Theme>
  );
};

export default AppHeader;

// Made with Bob
